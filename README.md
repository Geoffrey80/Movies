# Movies

Application Python Streamlit avec MongoDB et Neo4j

**Groupe 45** : Geoffrey GUESDON, Joel GUEMTCHUENG KOM, Oumar DIAWARA

Cette application permet de visualiser et d'interagir avec les données contenues dans le fichier `movies.json`. 
L'interface est facile à utiliser grâce à un menu déroulant situé en `haut à gauche`, permettant de naviguer entre les différentes pages de l'application.

Il y a **trois pages principales** avec des fonctionnalités distinctes :

## 1. Recherche de Films

Sur cette page, vous pouvez affiner vos recherches en sélectionnant les films selon plusieurs critères :
- **Année de sortie** : Vous pouvez filtrer les films en fonction de leur année de sortie.
- **Genres** : Une liste déroulante vous permet de sélectionner un ou plusieurs genres pour affiner la recherche. Vous pouvez combiner différents genres pour des résultats plus précis.
- **Classement** : Vous pouvez filtrer les films selon leur classement, qui varie de 0 à 100.
- **Revenus** : Un autre critère vous permet de trier les films en fonction des revenus générés au box-office.

Les filtres peuvent être combinés de manière flexible, ou utilisés indépendamment, selon vos besoins. Par exemple, vous pouvez rechercher des films spécifiques à un genre, une année et un classement particulier.

Deux boutons permettent également de filtrer les films en fonction de leur **durée** :
- **Films courts**
- **Films longs**

En bas de la page, le nombre de films trouvés s'affiche toujours. Si aucune combinaison ne donne de résultats, cela signifie qu'aucun film ne correspond aux critères sélectionnés dans la base de données.

## 2. Classement

Cette page présente un **graphe interactif** représentant les relations entre les acteurs, les réalisateurs et les films. Le graphe montre les collaborations entre ces différentes personnes et permet d'explorer plusieurs aspects :
- Qui sont les acteurs et réalisateurs ayant participé aux films les plus populaires ?
- Quels sont les genres de films favoris de certains acteurs ou réalisateurs ?
- Qui sont les réalisateurs qui ont produit les meilleurs films en termes de revenus ou de popularité ?
- Quels acteurs jouent dans ces films à succès ?

En bas de cette page, vous trouverez un **podium des films les plus populaires**, basé sur divers critères de succès tels que les revenus ou les évaluations.

## 3. Analyse

La troisième page présente des **graphes d'analyse** pour explorer les tendances du cinéma au fil du temps :
- **Premier histogramme** : Cet histogramme affiche les revenus générés par les films au fil des années, avec un tri possible par genre. Vous pouvez également combiner plusieurs genres pour identifier les types de films les plus populaires.
- **Deuxième histogramme** : Ce graphique présente la durée moyenne des films en fonction de leurs revenus, permettant d'analyser si les films longs ou courts génèrent plus de revenus.
- **Troisième histogramme** : Ce graphique montre l'évolution des films par décennie, en fonction de leur durée moyenne et des genres dominants, accompagné d'un **camembert** pour une visualisation plus claire.

Ces outils vous permettent d'explorer les données et d'identifier des tendances intéressantes concernant les films, leur succès et leur évolution au fil des années.

# Prérequis 

Pour la communication entre MongoDB et Neo4j, on utilise les codes d'identifiant pour se connecter.

Les codes et tout les informations de connexion se trouve dans le dossier `.streamlit` où se trouve le fichier `secrets.toml` comportant l'ensemble de vos paramètres
de connexions pour les deux bases de données, il est très important de vérifier sinon les bases de données ne pourront jamais communiquer.

De plus, le fichier `movies.json` doit être obligatoirement renseigné dans votre base de donnée MongoDB, aussi tout les commandes ont été fait avec pour nom de collection utilisateurs,
pour le bon fonctionnement de l'application je prie d'utiliser le même de collection dans de l'importation sur mongodb.

commande en Linux:
`mongoimport --uri="mongodb://user:root@localhost:27017/movies?authSource=admin" --collection=utilisateurs --file=movies.jsoni`

Le dossier `cover` regroupe l'ensemble des images utilisé dans l'application.

# Dépendances

Voici les bibliothèques nécessaires pour faire fonctionner ce projet, ainsi qu'une brève explication de leur utilisation : 

### Attention : Python3 est essentiel sans ça il est impossible de lancer ou d'utiliser l'application !!!

### 1. **streamlit**
   - **Installation** : `pip install streamlit`
   - **Description** : Permet de créer l'applications web interactives en Python.

### 2. **streamlit-option-menu**
   - **Installation** : `pip install streamlit-option-menu`
   - **Description** : Permet d'ajouter un menu d'options dans l'interface Streamlit. Il permet d'obtenir plusieurs page avec le menu déroulant sur un code.

### 3. **Pillow (PIL)**
   - **Installation** : `pip install pillow`
   - **Description** : Bibliothèque pour la manipulation d'images en Python. Elle est utilisée pour l'afficahge d'image sur la page d'acceuil.

### 4. **neo4j**
   - **Installation** : `pip install neo4j`
   - **Description** : Fournit une interface pour interagir avec la base de données de graphes Neo4j.

### 5. **pymongo**
   - **Installation** : `pip install pymongo`
   - **Description** : Permet d'interagir avec la base de données MongoDB. On récupére les données sous forme de documents JSON dans cette application.

### 6. **plotly**
   - **Installation** : `pip install plotly`
   - **Description** : Permet de créer des graphiques interactifs, comme des graphiques à barres ou des courbes, et de les afficher dans l'application.

### 7. **streamlit-echarts**
   - **Installation** : `pip install streamlit-echarts`
   - **Description** : Permet d'intégrer des graphiques interactifs basés sur ECharts dans Streamlit. Utilisé dans la page Classement.

### 8. **pandas**
   - **Installation** : `pip install pandas`
   - **Description** : Permet de charger, nettoyer et analyser des données sous forme de tableaux (DataFrame) pour rassembler et calculer les données entre eux.

### 9. **numpy**
   - **Installation** : `pip install numpy`
   - **Description** : Effectuer des calculs rapides sur des tableaux multidimensionnels et des matrices.

### Bibliothèques incluses par défaut :
Les bibliothèques suivantes font partie de Python et n'ont pas besoin d'être installées :

- **base64** : Utilisé pour encoder et décoder des données binaires en texte ASCII les images de la page d'Accueil.
- **io** : Fournit des outils pour travailler avec les flux de données en mémoire, important pour streamlit lorsque tout est actualise au moindre clic.
- **json** : On utilise la base de données d'un fichier json dans Mongodb.
- **random** : Génère des nombres aléatoires.
- **glob** : Utilisé pour trouver tous les fichiers qui correspondent à un modèle de chemin donné.
- **pathlib** : Fournit une interface orientée objet pour manipuler les chemins de fichiers.
