#!/usr/bin/env python3

import streamlit as st
import base64
from streamlit_option_menu import option_menu
from PIL import Image
from io import BytesIO
import json
from neo4j import GraphDatabase
import random
import glob
import os
import pymongo
import plotly.express as px
from pathlib import Path
from streamlit_echarts import st_echarts
import pandas as pd
import numpy as np


# Ajout du nom et du logo du site dans la barre d'onglet
# Empêche la barre menu de s'ouvrir lorsqu'on accède au site
# Ajuste la longueur des textes sur les pages pour éviter un retour à la ligne trop rapide
st.set_page_config(page_title="Movies", page_icon=":clapper:", layout="wide", initial_sidebar_state="collapsed")

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
            {"$or": [
                {"genre": {"$exists": True}},
                {"Actors": {"$exists": True}}
            ]},
            [
                {
                    "$set": {
                        "genre": {
                            "$cond": {
                                "if": {"$isArray": "$genre"},
                                "then": "$genre",
                                "else": {"$split": ["$genre", ","]}
                            }
                        },
                        "Actors": {
                            "$cond": {
                                "if": {"$isArray": "$Actors"},
                                "then": "$Actors",
                                "else": {"$split": ["$Actors", ","]}
                            }
                        }
                    }
                }
            ]
        )
    
    except Exception as e:
        st.error(f"Erreur lors de la mise à jour : {e}")

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

def init_neo4j_connection():
    neo4j_credentials = st.secrets["neo4j"]
    uri = neo4j_credentials["uri"]
    user = neo4j_credentials["user"]
    password = neo4j_credentials["password"]
    return GraphDatabase.driver(uri, auth=(user, password))

# Connexion à Neo4j
neo4j_client = init_neo4j_connection()
session = neo4j_client.session()

def clean_neo4j():
    # Supprimer tous les films, acteurs et réalisateurs de la base Neo4j
    clean_query = """
    MATCH (n)
    DETACH DELETE n
    """
    try:
        session.run(clean_query)
        print("Les anciennes données ont été supprimées de Neo4j.")
    except Exception as e:
        print(f"Erreur lors de la suppression des données : {e}")

def import_movies_to_neo4j():
    clean_neo4j()
    for movie in db.utilisateurs.find():  # Parcours chaque film dans la collection MongoDB

        # Vérification des valeurs manquantes ou invalides dans les champs avant de créer un nœud Film
        movie_id = movie.get('_id', 'Unknown ID')
        title = movie.get('title', 'Unknown Title').replace("'", "\\'")  # Échappe les apostrophes
        year = movie.get('year', 'Unknown Year')
        votes = movie.get('Votes', 0)  # Valeur par défaut 0 si 'Votes' est manquant
        revenue = movie.get('Revenue (Millions)', 0)  # Valeur par défaut 0 si 'Revenue' est manquant

        if revenue == "" or revenue == "NA":
            revenue = 0

        # Construction de la requête en gérant les valeurs manquantes
        movie_query = f"""
        MERGE (m:Film {{id: {movie_id}, title: '{title}', year: {year}, votes: {votes}, revenue: {revenue}}})
        """

        # Exécuter la requête pour créer ou mettre à jour le film
        session.run(movie_query)

        # Créer des nœuds Actor et des relations "A_JOUER" entre les films et les acteurs
        if "Actors" in movie:  # Vérifie si des acteurs existent pour ce film
            for actor in movie['Actors']:
                actor = actor.replace("'", "\\'")  # Échapper les apostrophes dans le nom de l'acteur
                actor_query = f"""
                MATCH (m:Film {{id: {movie_id}}})
                MERGE (a:Actor {{name: '{actor}'}})
                MERGE (a)-[:A_JOUER]->(m)
                """
                session.run(actor_query)  # Exécuter la requête de l'acteur

        # Créer des nœuds Realisateur et des relations "REALISE_PAR" entre le film et les réalisateurs
        if "Director" in movie:  # Vérifie si des réalisateurs existent pour ce film
            director = movie['Director']
            if isinstance(director, list):  # Si plusieurs réalisateurs
                for realisateur in director:
                    realisateur = realisateur.replace("'", "\\'")  # Échapper les apostrophes dans le nom du réalisateur
                    director_query = f"""
                    MATCH (m:Film {{id: {movie_id}}})
                    MERGE (r:Realisateur {{name: '{realisateur}'}})
                    MERGE (m)-[:REALISE_PAR]->(r)
                    """
                    session.run(director_query)  # Exécuter la requête pour chaque réalisateur
            else:  # Si un seul réalisateur
                director = director.replace("'", "\\'")  # Échapper les apostrophes
                director_query = f"""
                MATCH (m:Film {{id: {movie_id}}})
                MERGE (r:Realisateur {{name: '{director}'}})
                MERGE (m)-[:REALISE_PAR]->(r)
                """
                session.run(director_query)  # Exécuter la requête pour le réalisateur

# Appel de la fonction pour importer les films
import_movies_to_neo4j()

# Menu de pages à gauche de l'application
with st.sidebar:
    page = option_menu(
            # Pas de titre Spécial
            menu_title= "",
            # Les noms des pages
            options=["Accueil", "Recherche de Films", "Classement", "Analyse"],
            # Les icones à gauches des noms des pages
            icons=["globe", "film", "trophy", "bar-chart-line"],
            # Page par default Accueil
            default_index=0,
            styles={
            "container": {"padding": "5px", "background-color": "#1a1a1a"},  # Fond gris foncé pour le container
            "icon": {"color": "#f1c40f", "font-size": "20px"},  # Icônes couleur or
            "nav-link": {
                "font-size": "18px",
                "font-weight": "bold",
                "color": "#ecf0f1",  # Texte couleur gris clair
                "text-align": "left",
                "margin": "5px",
                "border-radius": "10px"
                },
                "nav-link-selected": {
                "background-color": "#34495e",  # Fond gris plus clair pour l'élément sélectionné
                "color": "#ecf0f1",  # Texte blanc pour l'élément sélectionné
                },
            }
        )

# Traitement de la page Accueil
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Traitement de la page Accueil
if page == "Accueil":

    # Charger les images depuis le dossier
    image_paths = glob.glob(os.path.expanduser("~/Movies/cover/*.jpg"))
    # CSS Global pour la mise en page et le style
    st.markdown(
        """
        <style>
        /* Appliquer un fond sombre pour un effet cinéma */
        .stApp {
            background: #000000;
            color: white;
            text-align: center;
        } 
        header[data-testid="stHeader"]::before {
            content: "";
            background: black;
            height: 100%;
            width: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 30px;
        }
        .section1 {
            display: flex;
            font-size: 20px;
            margin: 30px;
            flex-direction: column;
            align-items: center;
        }
        .section2 {
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            margin: 30px;
        }
        .text { 
            max-width: 500px;  /* Limiter la largeur du texte */
            padding-top: 350px;
            font-size: 30px;  /* Augmenter la taille de la police du texte */
            line-height: 1.6;
            flex-grow: 1;  /* Permet au texte de s'étendre sans modifier la taille des images */
            margin-left: 20px;
        }
        .gallery {
            display: flex;
            justify-content: flex-start;
            gap: 20px;
            margin-top: 30px;
        }
        .column {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .column img {
            width: 400px;
            height: auto;
            border-radius: 10px;
            box-shadow: 3px 3px 10px rgba(0, 0, 0, 0.5);
            transform: rotate(var(--rotation));
            transition: transform 0.3s ease;
        }
        .column img:hover {
            transform: scale(1.05);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    # Premier bloc : Présentation projet
    st.markdown(
        """
        <div class="section1">
            <h1>🎬 Bienvenue sur Movies Data Visualization</h1>
            <p>
            Dans ce projet, nous avons exploré et intégré deux systèmes de gestion de bases de données NoSQL : MongoDB, une base de données orientée document, et Neo4j,
            une base de données orientée graphe. En développant une application Python interactive avec Streamlit, 
            nous avons créé une interface permettant d’interagir facilement avec ces bases de données cloud.
            L’application permet non seulement d’établir une connexion sécurisée avec MongoDB et Neo4j, mais aussi de réaliser des requêtes avancées pour récupérer, 
            analyser et visualiser des données pertinentes. Que ce soit pour manipuler des documents avec MongoDB ou pour naviguer dans des graphes complexes avec Neo4j,
            notre projet vous propose une solution complète et intuitive pour interroger et explorer ces systèmes de bases de données NoSQL. <br> 
            <br>Explorez notre travail, découvrez les fonctionnalités de notre application et plongez dans l'univers des bases de données NoSQL !</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Deuxième bloc : galerie de 12 images
    if len(image_paths) >= 12:
        selected_images = image_paths[:12] 
        image_base64_list = [get_base64_image(img) for img in selected_images]

        image_html = f"""
        <div class="section2">
            <div class="gallery">
                <div class="column">
                    <img src="data:image/jpg;base64,{image_base64_list[0]}">
                    <img src="data:image/jpg;base64,{image_base64_list[1]}">
                    <img src="data:image/jpg;base64,{image_base64_list[2]}">
                </div>
                <div class="column">
                    <img src="data:image/jpg;base64,{image_base64_list[3]}">
                    <img src="data:image/jpg;base64,{image_base64_list[4]}">
                    <img src="data:image/jpg;base64,{image_base64_list[5]}">
                </div>
                <div class="column">
                    <img src="data:image/jpg;base64,{image_base64_list[6]}">
                    <img src="data:image/jpg;base64,{image_base64_list[7]}">
                    <img src="data:image/jpg;base64,{image_base64_list[8]}">
                </div>
                <div class="column">
                    <img src="data:image/jpg;base64,{image_base64_list[9]}">
                    <img src="data:image/jpg;base64,{image_base64_list[10]}">
                    <img src="data:image/jpg;base64,{image_base64_list[11]}">
                </div>
            </div>
            <div class="text">
                <h2>Les Films que vous aimez !</h2>
                <p>Classiques ● Action ● Adventure ● Biography ● Comedy ● Horror ● Drama ● Fantasy ● Science-Fiction ● Western
                ● Family ● Mystery ● War ● History ● Romance ● Thriller ● Crime ● Music ● Animation
                </p>
            </div>
        </div>
        """

        st.markdown(image_html, unsafe_allow_html=True)
    else:
        st.error("Pas assez d'images disponibles (minimum 12 requises).")

# Traitement de la page Recherche de Films
elif page == "Recherche de Films":
    st.markdown(
        """
        <style>
        /* Appliquer un fond sombre pour un effet cinéma */
        .stApp {
            background: #E0CDA9;
            color: black;
            text-align: start;
        } 
        header[data-testid="stHeader"]::before {
            content: "";
            background: #E0CDA9;
            height: 100%;
            width: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

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

    rang_minimun = st.number_input("Entrez le rang minimun du film [0-100]:")
    revenue_minimun = st.number_input("Entrez le revenue minimun du film [0 - 1000] :")
    
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
        films = db.utilisateurs.find({"year": selected_year, "genre": {"$all": selected_genre}, "Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous" and selected_genre:
        films = db.utilisateurs.find({"year": selected_year, "genre": {"$all": selected_genre}})
    elif selected_year != "Tous" and rang_minimun and  revenue_minimun:
        films = db.distributions.film({"year": selected_year, "Revenue (Millions)": {"gte" : revenue_minimun, "$nin": ["NA", "None", ""]}, "Metascore": {"$gte": rang_minimun, "$nin": ["NA", "None", ""]}})
    elif selected_year != "Tous" and rang_minimun:
        films = db.utilisateurs.find({"year": selected_year, "Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year != "Tous" and revenue_minimun:
        films = db.utilisateurs.find({"year": selected_year, "Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and selected_genre and rang_minimun and revenue_minimun:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}, "Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}, "Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and selected_genre and rang_minimun:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}, "Metascore": {"$gte" : rang_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and selected_genre and revenue_minimun:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}, "Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and rang_minimun and revenue_minimun:
        films = db.utilisateurs.find({"Metascore": {"$gt" : rang_minimun, "$nin" : ["NA", "None", ""]}, "Revenue (Millions)": {"$gt": revenue_minimun, "$nin" : ["NA", "None", ""]}}) 
    elif selected_year == "Tous" and selected_genre:
        films = db.utilisateurs.find({"genre": {"$all": selected_genre}})
    elif selected_year == "Tous" and revenue_minimun:
        films = db.utilisateurs.find({"Revenue (Millions)": {"$gte" : revenue_minimun, "$nin" : ["NA", "None", ""]}})
    elif selected_year == "Tous" and rang_minimun:
        films = db.utilisateurs.find({"Metascore": {"$gte": rang_minimun, "$nin": ["NA", "None", ""]}})
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
            if "Metascore" in film and film["Metascore"] not in ["NA", "None", ""]:
                st.write(f"Classement : {film["Metascore"]}")
            st.write(f"Synopsis : {film["Description"]}")
            if "Revenue (Millions)" in film and film["Revenue (Millions)"] not in ["NA", "None", ""]:
                st.write(f"Revenue : {film["Revenue (Millions)"]}")
            st.write(f"Durée : {film["Runtime (Minutes)"]}")
            st.write(f"Année : {film["year"]}")
            st.markdown("<hr style='border: 1px solid #CCCCCC;'>", unsafe_allow_html=True)        
    else:
        st.write("Aucun film trouvé pour cette année.")

# Page de Classsement
elif page == "Classement":

    st.markdown(
        """
        <style>
        /* Appliquer un fond sombre pour un effet cinéma */
        .stApp {
            background: white;
            color: black;
            text-align: start;
        }
        header[data-testid="stHeader"]::before {
            content: "";
            background: #000000;
            height: 100%;
            width: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("Graphique des relations dans la base Neo4j")
        
    # Exécuter la requête Neo4j pour récupérer toutes les relations
    query = """
    MATCH p=()-[]->() 
    RETURN p;
    """
    results = session.run(query)

    # Initialisation des structures de stockage
    nodes = []
    links = []
    categories = []
    node_dict = {}  # Dictionnaire pour stocker les nœuds uniques
    category_dict = {}  # Dictionnaire pour stocker les catégories dynamiquement

    # Traiter les résultats
    for record in results:
        # Récupérer tous les nœuds et relations impliqués dans le chemin
        for rel in record["p"].relationships:
            start_node = rel.start_node
            end_node = rel.end_node
            relation_type = rel.type  # Type de relation (ex: A_JOUER, REALISE_PAR, etc.)

            # Ajouter le type de nœud à category_dict s'il n'existe pas
            for node in [start_node, end_node]:
                node_label = list(node.labels)[0]  # Prendre la première étiquette du nœud
                if node_label not in category_dict:
                    category_dict[node_label] = len(category_dict)
                    categories.append({"name": node_label})

                # Ajouter le nœud dans node_dict s'il n'existe pas encore
                node_id = node["name"] if "name" in node else node["title"]
                if node_id not in node_dict:
                    node_dict[node_id] = {
                        "name": node_id,
                        "symbolSize": 40 if node_label == "Film" else 30,
                        "category": category_dict[node_label],  # Assigner la catégorie dynamiquement
                    }
                    nodes.append(node_dict[node_id])

            # Ajouter la relation dans links
            links.append({
                "source": start_node["name"] if "name" in start_node else start_node["title"],
                "target": end_node["name"] if "name" in end_node else end_node["title"],
                "value": relation_type  # Nom de la relation
            })

    # Préparer la configuration pour ECharts
    option = {
        "tooltip": {
            "show": True,
            "formatter": "{b}"  # Affiche uniquement le nom de l'élément sous la souris
        },
        "legend": [
            {
                "data": [category["name"] for category in categories],
                "selectedMode": "multiple",
                "textStyle": {"fontSize": 12},
            }
        ],
        "animationDuration": 2000,
        "animationEasingUpdate": "quinticInOut",
        "series": [
            {
                "name": "Entités et Relations",
                "type": "graph",
                "layout": "force",  # Utilise le layout "force" pour gérer les positions des nœuds
                "force": {
                    "repulsion": 250,  # Augmente la distance entre les nœuds
                    "edgeLength": [50, 200],  # Ajuste la longueur des liens
                },
                "data": nodes,  # Liste des nœuds récupérés
                "links": links,  # Liste des liens récupérés
                "categories": categories,  # Catégories détectées dynamiquement
                "roam": True,  # Permet de déplacer le graphique et d'utiliser le zoom
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{b}",
                    "fontSize": 12,
                },
                "lineStyle": {
                    "color": "source",
                    "curveness": 0.2,
                    "opacity": 0.8,
                },
                "emphasis": {
                    "focus": "adjacency",
                    "lineStyle": {"width": 2},
                    "label": {"fontSize": 14, "fontWeight": "bold"},
                },
                "symbolSize": 10,
            }
        ],
    }

    # Afficher le graphique avec Streamlit
    st_echarts(option, height="1000px")

    st.markdown("<hr style='border: 1px solid #CCCCCC; color: black'>", unsafe_allow_html=True)
    st.write("TOP 3 des Films les mieux notés !")

    # Récupérer les films avec une note et les trier pour obtenir le top 3
    classement = db.utilisateurs.find({"rating": {"$ne": "unrated"}})
    top_3 = list(classement.sort([("rating", pymongo.DESCENDING), ("Votes", pymongo.DESCENDING)]).limit(3))

    if len(top_3) > 0:
    # Utiliser st.columns pour afficher les films côte à côte
        cols = st.columns(3)  # Créer 3 colonnes pour les 3 films

        for i, top in enumerate(top_3):
        # Définir la couleur selon la position
            if i == 0:
                color = "#FFD700"  # Or
            elif i == 1:
                color = "#C0C0C0"  # Argent
            else:
                color = "#CD7F32"  # Bronze

            with cols[i]:
                st.markdown(f"""
                <br>
                <div style="background-color: {color}; 
                    padding: 20px; 
                    border-radius: 50%; 
                    width: 180px; 
                    height: 180px; 
                    display: flex; 
                    flex-direction: 
                    column; justify-content: center; 
                    align-items: center; 
                    text-align: center; 
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);">
                    <strong>{i+1}. {top["title"]}</strong>
                    <small>Rating: {top["rating"]}</small>
                    <small>Votes: {top["Votes"]}</small>
                </div>
                <br>
                """, unsafe_allow_html=True)

# Page Analyse
elif page == "Analyse":
    st.markdown(
        """
        <style>
        .stApp {
            background: #E0CDA9;
            color: black;
            text-align: start;
        }
        header[data-testid="stHeader"]::before {
            content: "";
            background: #E0CDA9;
            height: 100%;
            width: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }

        </style>
        """,
        unsafe_allow_html=True
    )
   
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

    # Affichage du graphique
    st.line_chart(df_ordre)
    # Affichage du tableau
    st.write("Observation des Résultats: Les revenus sont exprimés en millions de dollars américains.")
    st.write(df_ordre)
    st.markdown("<hr style='border: 1px solid #CCCCCC; color: black'>", unsafe_allow_html=True)

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
    st.markdown("<hr style='border: 1px solid #CCCCCC;'>", unsafe_allow_html=True)
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

