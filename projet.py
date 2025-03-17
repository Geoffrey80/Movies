#!/usr/bin/env python3

# Librairie principale pour l'application python3
import streamlit as st
# Librairie pour le menu de pages à gauche de l'application
from streamlit_option_menu import option_menu
# Librairie pour intéragir avec MongoDB
import pymongo
import plotly.express as px
import pandas as pd
import numpy as np

# Fonction pour établir la communication à MongoDB avec les paramètres de sécurité saisie dans le fichier qui se trouve dans  ~/<dossier_du_projet/.streamlit/secrets.toml
def init_connection():
    return pymongo.MongoClient(**st.secrets["mongo"])

# Etablit la connexion via MongoDB
client = init_connection()

# Récupére la base de donnée movies
db = client.movies

# Nettoyage des documents dans Movies on remarque qu'aucun film n'est renseigné pour les documents avec un _id débutant avec _design
# Fonction de suppression des documents indésirables dans Movies
def remove_design_documents():
    try:
        # Suppression des documents où _id commence par '_design'
        remove = db.utilisateurs.delete_many({"_id": {"$regex": "^_design"}})
    # En cas d'échec de la suppresion
    except Exception as e:
        st.error(f"Erreur lors de la suppression : {e}")

# Mise à jour de la variable genre due à différents genre sépare par des ',' tel qu'un genre d'un film est défini comme Action,Adventure,Sci-FI
# Décomposer les différents caractéristiques du genre afin d'obtenir une liste de genre comprenant Action puis Adventure et Sci-Fi pour un même film
# Afin d'obtenir non pas un genre : Action,Adventure et Sci-fi mais le genre : Action et le genre : Adventure et le genre: Sci-fi
def update_documents():
    try:
        result = db.utilisateurs.update_many(
            {"genre": {"$exists": True}},
            [
                {
                    "$set":{
                        "genre": {
                            "$cond": {
                                "if": {"$isArray": "$genre"},
                                "then": "$genre",
                                "else" : {"$split": ["$genre", ","]}
                            }
                        }
                    }
                }
            ]
        ) 
    # En cas d'échec de la mise à jour
    except Exception as e:
        st.error(f"Errreur lors de la mise à jour : {e}")

# Nettoyage de la base de donnée MongoDB movies
remove_design_documents()
# Mise à jour des documents MongoDB movies
update_documents()
# Décompose la liste genre pour créer des éléments individuels
new_genre = [{"$unwind": "$genre"},
    # Regroupe les éléments individuels entre eux | ex: l'élément "Action" va regrouper tout les fims qui ont le genre "Action"
    {"$group": {"_id": "$genre"}}]

# Agrégations des élements individuels de la base de données
# Attention en aucun cas elle met à jour la base de donnée
# c.a.d : "Elle fait une lecture d'analyse des documents" à prendre avec des pincettes
result = db.utilisateurs.aggregate(new_genre)

# Menu de pages à gauche de l'application
with st.sidebar:
    page = option_menu(
            # Pas de titre Spécial
            menu_title= "",
            # Les noms des pages
            options=["Accueil", "Recherche de Films", "Classement", "Analyse"],
            # Les icones à gauches des noms des pages
            icons=["globe", "film", "trophy", "bar-chart-line"])

# Traitement de la page Accueil
if page == "Accueil":
    st.title("Bienvenue dans l'application Movies Stars")
    st.write("Une application pour rechercher vos films de votre base de donnée Mongodb")
    st.write("Vous pourrez parcourir l'ensemble des informations avec une analyse concrète de l'ensemble des informations")

# Traitement de la page Recherche de Films
elif page == "Recherche de Films":
    st.title("Recherche de Films par Années !")
    
    # Filtre les films par année
    year = db.utilisateurs.distinct("year")
    # Trie les années par ordre décroissant grâce au reverse
    year.sort(reverse=True)
    # Insertion de l'options 'Tous' pour afficher les films de tous les années
    year.insert(0, "Tous")
    # Sélection déroulante de l'ensemble des années
    selected_year = st.selectbox("Sélectionne une année :", year)

    # Trie par ordre Alphabétique les genres distinct extrait des élements individuels dans result via '_id'
    genre = sorted([r['_id'] for r in result])
    # Sélection déroulante des types de genres à choix multiples
    selected_genre = st.multiselect("Sélectionne un ou plusieurs genres :", genre)
    
    def verification_saisie(nombre):
        try:
            float(nombre)
            return True
        except ValueError:
            st.error("Veuillez saisir un nombre valide.")
            return False

    rang_minimun = st.number_input("Entrez le rang minimun du film :")
    revenue_minimun = st.number_input("Entrez le revenue minimun du film :")
    
    if verification_saisie(rang_minimun):
        st.write(f"Le rang minimun des films est {rang_minimun}.")
    else:
        st.write(f"Le rang minimun des films {rang_minimun} est erroné.")

    if verification_saisie(revenue_minimun):
        st.write(f"Le revenue minimun des films est {revenue_minimun}.")
    else:
        st.write(f"Le revenue minimun des films {revenue_minimun} est non conforme.")

    # Vérifie si la clé "time" n'existe pas déjà dans l'état de la session
    if "time" not in st.session_state:
        # Si la clé "time" n'existe pas, on l'initialise à None
        st.session_state.time = None
    
    # Vérifie si la clé "click" n'existe pas déjà dans l'état de la session
    if "click" not in st.session_state:
        # Si la clé "click" n'existe pas, on l'initialise à None
        st.session_state.click = None

    ###########  PROBLEM le bouton ne reste pas rouge après avoir clické ailleurs malgré la persistance de son activation
      ######     PROBLEM due au fonctionnement de Streamlit selon mes recherches sur Stackoverflow

    ########### changement de couleur lorsque le bouton est on mais sa persistance ne marche pas
    ########### fonction non utilisé
    def button_style(button_name):
        if st.session_state.click == button_name:
            return "background-color: yelllow; color: white;"
        return "background-color: gray; color: black;"
    ###########
    ###########


    # Création de deux colonnes sur la même ligne
    time1, time2=st.columns(2)
    
    # Traitement de la première colonne
    with time1:
        
        #button_style_short = button_style("short") DESIGN DU BOUTON NON UTILISE EN RAISON DES PROBLEMES EXPLIQUES
        
        # Création du bouton 'Film court' et message d'indication lors du maintien
        if st.button("Film court", key="short", help="Affiche les films les plus courts"):
            # La variable 'click' dans la session est égale 'short' cela signifie que le bouton a été précedemment activé
            if st.session_state.click == "short":
                # Réinitialisation des variables 'time' et 'click' lorsqu'on désactive l'état du bouton 'Film court'
                st.session_state.time = None # Annule l'affichage des films courts et se met par default
                st.session_state.click = None # Désactive l'état de sélection du bouton, bouton = off

            # la variable 'click' dans la session n'est pas 'short' alors l'état du bouton n'est pas activé
            else:
                # Activation du bouton 'Film court' en définissant 'time' et 'click' avec des nouvelles valeurs
                st.session_state.time = 1 # Définit time a 1 pour les films courts
                st.session_state.click = "short" # Marque le bouton 'Film court' activé, bouton = on
    
    # Traitement de la seconde colonne
    with time2:

        #button_style_long = button_style("long") DESIGN DU BOUTON NON UTILISE EN RAISON DES PROBLEMES EXPLIQUES
        
        # Création du bouton 'Film long' et message d'indication lors du maintien
        if st.button("Film long", key="long", help="Affiche les films les plus longs"):
            # La variable 'click' dans la session est égale 'long' cela signifie que le bouton a été précedemment activé
            if st.session_state.click == "long":
                # Réinitialisation des variables 'time' et 'click' lorsqu'on désactive l'état du bouton 'Film long'
                st.session_state.time = None # Annule l'affichage des films longs et set met par default
                st.session_state.click = None # Désactive l'état de sélection du bouton, bouton = off
            
            # la variable 'click' dans la session n'est pas 'long' alors l'état du bouton n'est pas activé
            else:
                # Activation du bouton 'Film long' en définissant 'time' et 'click' avec des nouvelles valeurs
                st.session_state.time = -1 # Définit time a 1 pour les films longs
                st.session_state.click = "long" # Marque le bouton 'Film long' activé, bouton = on

    # Trie les films par années et genre et rang et revenue | option "Tous" signifie prendre tous les films disponible sans les années
    if selected_year != "Tous" and selected_genre and rang_minimun and revenue_minimun:
        films = db.utilisateurs.find({"year": selected_year, "genre": {"$all": selected_genre}, "Metascore": {"$gt" : rang_minimun, "$nin" : ["NA", "None", ""]}, "Revenue (Millions)": {"$gt": revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous" and rang_minimun and revenue_minimun:
        films = db.utilisateurs.find({"year": selected_year, "Metascore": {"$gt" : rang_minimun, "$nin" : ["NA", "None", ""]}, "Revenue (Millions)": {"$gt": revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous" and selected_genre and rang_minimun:
        films = db.utilisateurs.find({"year": selected_year, "genre": {"$all": selected_genre}, "Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous" and selected_genre and revenue_minimun:
        films = db.utilisateurs.find({"year": selected_year, "genre": {"$all": selected_genre}, "Metascore": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous" and selected_genre:
        films = db.utilisateurs.find({"year": selected_year, "genre": {"$all": selected_genre}})
    elif selected_year != "Tous" and rang_minimun:
        films = db.utilisateurs.find({"year": selected_year, "Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and revenue_minimun:
        films = db.utilisateurs.find({"year": selected_year, "Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and selected_genre and rang_minimun:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}, "Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and selected_genre and revenue_minimun:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}, "Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and selected_genre:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}})
    elif selected_year == "Tous" and rang_minimun:
        films = db.utilisateurs.find({"Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and revenue_minimun:
        films = db.utilisateurs.find({"Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous":
        films = db.utilisateurs.find({"year": selected_year})
    else:
        films = db.utilisateurs.find()

    # Activer les effets des boutons Film court et Film long
    if st.session_state.time is None:
        # cas où le bouton est off mettre par default
        films_time = films.sort("title", 1)
    else:
        # cas où le bouton est on
        time = 1 if st.session_state.time == 1 else -1
        films_time = films.sort("Runtime (Minutes)", time)

    # Place dans une liste la recherche du film avec l'état des deux bouton 'Film court' et 'Film long'
    films_list = list(films_time)
    if len(films_list) > 0:
        st.subheader(f"Films de l'année {selected_year} : {len(films_list)} films trouvés")
        for film in films_list:
            st.write(f"Nom du Film : {film["title"]}")
            st.write(f"Genre du Film : {', '.join(film['genre'])}")
            st.write(f"Réalisateur : {film["Director"]}")
            if "Metascore" in film and film["Metascore"] not in ["NA", None, ""]:
                st.write(f"Classement : {film["Metascore"]}")
            st.write(f"Synopsis : {film["Description"]}")
            if "Revenue (Millions)" in film and film["Revenue (Millions)"] not in ["NA", None, ""]:
                st.write(f"Revenue : {film["Revenue (Millions)"]}")
            st.write(f"Durée : {film["Runtime (Minutes)"]}")
            st.write(f"Année : {film["year"]}")
            st.markdown("<hr style='border: 1px solid #CCCCCC;'>", unsafe_allow_html=True)        
    else:
        st.write("Aucun film trouvé pour cette année.")

elif page == "Classement":
    st.title("TOP 3 des Films les mieux notés !")

    # Récupérer les films avec une note et les trier pour obtenir le top 3
    classement = db.utilisateurs.find({"rating": {"$ne": "unrated"}})
    top_3 = list(classement.sort([("rating", pymongo.DESCENDING), ("Votes", pymongo.DESCENDING)]).limit(3))

    if len(top_3) > 0:
        # Utiliser st.columns pour afficher les films côte à côte
        cols = st.columns(3)  # Créer 3 colonnes pour les 3 films

        for i, top in enumerate(top_3):
            with cols[i]:
                st.markdown(f"""
                <br>
                <div style="background-color: #f0f0f0; padding: 20px; border-radius: 50%; width: 180px; height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);">
                    <strong>{i+1}.{top["title"]}</strong>
                    <small>Rating: {top["rating"]}</small>
                    <small>Votes: {top["Votes"]}</small>
                </div>
                <br>
                """, unsafe_allow_html=True)

    else:
        st.write("Les films n'ont pas été notés !")

elif page == "Analyse":
   
    # Première Partie : les meilleurs revenue en fonction du genre et de l'année

    st.title("Analyse des différents documents dans Movies")
    st.subheader("Les Films avec les meilleurs Revenues en fonction du Genre par Année")
    
    # Trie par ordre Alphabétique les genres distinct extrait des élements individuels dans result via '_id'
    genre = sorted([r['_id'] for r in result])
    # Sélection déroulante des types de genres à choix multiples
    selected_genre = st.multiselect("Sélectionne un ou plusieurs genres :", genre)
    
    stats = list(db.utilisateurs.find({"genre": {"$all": selected_genre, "$exists": True}, "year": {"$exists": True}, "Revenue (Millions)": {"$nin" : ["NA", "Node", ""], "$exists" : True }}))
    
    genre_year_revenue_data = [(genre, x["year"], x.get("Revenue (Millions)", "")) for x in stats for genre in x["genre"]]
    
    df = pd.DataFrame(genre_year_revenue_data, columns=["Genre", "Année", "Revenue"])
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")

    if selected_genre:
        df = df[df["Genre"].isin(selected_genre)]
    
    df_resultat = df.groupby(["Année", "Genre"]).agg(median_revenue = pd.NamedAgg(column="Revenue", aggfunc="median")).reset_index()
    # Fusion des genres dans le cas de la sélection de plusieurs genres
    df_resultat["Genres"] = df_resultat.groupby("Année")["Genre"].transform(lambda x: ', '.join(sorted(x.unique()))) 
    # Avoir l'année comme index et les genres comme colonnes
    df_ordre = df_resultat.pivot_table(index="Année", columns="Genres", values="median_revenue", aggfunc="median")
    
    # Correction de l'affichage des Années : 2016 au lieu de 2,016.0
    df_ordre.index = df_ordre.index.astype(str)
    # Correction de l'affichage des Années de verticale à horizontale
    

    # Affichage du graphique
    st.line_chart(df_ordre)
    # Affichage du tableau
    st.write("Observation des Résultats: Les revenus sont exprimés en millions de dollars américains.")
    st.write(df_ordre)
    st.markdown("<hr style='border: 1px solid #CCCCCC;'>", unsafe_allow_html=True)

###################### Deuxième Partie : Relation entre la Durée des Film et leur revenue ###############

    st.subheader("Les Revenues  en fonction de la Durée du Film")
    stats_duree = list(db.utilisateurs.find({"Runtime (Minutes)": {"$exists": True}, "Revenue (Millions)": {"$nin": ["NA", "Node", ""], "$exists" : True}}))
    revenue_duree = [(x["Runtime (Minutes)"], x.get("Revenue (Millions)", "")) for x in stats_duree]

    df_2 = pd.DataFrame(revenue_duree, columns = ["Duree", "Revenue"])
    df_2["Duree"]= pd.to_numeric(df_2["Duree"], errors="coerce")
    df_2["Revenue"]= pd.to_numeric(df_2["Revenue"], errors="coerce")
    
    df_result = df_2.groupby(["Duree"]).agg(median_revenues = pd.NamedAgg(column="Revenue", aggfunc="median")).reset_index()
    
    def convertir_minutes_en_HeureMinute(minutes):
        heures = minutes // 60
        mins = minutes % 60
        return f"{heures}h {mins}m"

    df_result["Duree_hm"] = df_result["Duree"].apply(convertir_minutes_en_HeureMinute) 

    st.line_chart(df_result.set_index("Duree")["median_revenues"])
    st.write("Observation des Résultats: Les revenus sont exprimés en millions de dollars américains.")
    st.dataframe(df_result[["Duree_hm", "median_revenues"]].set_index("Duree_hm"))

############ Troisième partie : Relation entre la moyenne de durée et les film par année ###########

    st.subheader("L'évolution de la durée moyenne des films par décennie")
    stats_evolution = list(db.utilisateurs.find({"year": {"$exists": True}, "Runtime (Minutes)": {"$exists": True}}))
    evolution_year = [(x["year"], x.get("Runtime (Minutes)", "")) for x in stats_evolution]

    df_3 = pd.DataFrame(evolution_year, columns = ["year", "Duree"])
    df_3["Duree"] = pd.to_numeric(df_3["Duree"], errors="coerce")
    df_3["decennie"] = (df_3["year"] // 10) * 10 
    df_evolution = df_3.groupby(["decennie"]).agg(median_duree= pd.NamedAgg(column="Duree", aggfunc='median')).reset_index()
    
    st.line_chart(df_evolution.set_index("decennie")["median_duree"])
    df_pie_duree = df_3.groupby("decennie")["Duree"].median().reset_index()

    # Utiliser la fonction de conversion pour afficher la durée en heures et minutes
    df_pie_duree["Duree_hm"] = df_pie_duree["Duree"].apply(convertir_minutes_en_HeureMinute)

    # Renommer la colonne "Duree" en "median_duree" pour que cela corresponde dans le graphique
    df_pie_duree = df_pie_duree.rename(columns={"Duree": "median_duree"})

    # Création du camembert avec Plotly
    fig = px.pie(df_pie_duree, names="decennie", values="median_duree", title="Répartition des films par Décennie", hover_data=["Duree_hm"])

    # Affichage du camembert dans Streamlit
    st.plotly_chart(fig)
