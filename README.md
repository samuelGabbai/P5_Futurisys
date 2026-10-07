# HRNova — Prédiction du départ des salariés

Projet 4 · TechNova Partners

Ce projet a pour objectif de prédire le risque de départ d’un salarié au sein d’une entreprise, à partir de données RH, d’évaluations et de sondages. L’objectif est d’identifier les facteurs associés au turnover et de construire un modèle exploitable pour la décision métier.

## Sommaire

- [Contexte métier](#contexte-métier)
- [Objectifs](#objectifs)
- [Structure du projet](#structure-du-projet)
- [Données](#données)
- [Installation](#installation)
- [Usage](#usage)
- [Méthodologie](#méthodologie)
- [Modèle retenu](#modèle-retenu)
- [Interprétabilité](#interprétabilité)
- [Résultats attendus](#résultats-attendus)
- [Limitations et améliorations possibles](#limitations-et-améliorations-possibles)
- [Auteur](#auteur)

## Contexte métier

Les départs au sein d’une organisation peuvent avoir un coût important en termes de recrutement, de productivité, de connaissance métier et de performance globale. Il est donc utile de détecter précocement les salariés les plus à risque de quitter l’entreprise afin de mettre en place des actions ciblées.

Le projet s’inscrit dans une logique :

- d’analyse des facteurs de départ,
- de modélisation prédictive,
- d’interprétation des décisions du modèle,
- de définition d’un seuil de décision adapté à un contexte déséquilibré.

## Objectifs

- Comprendre la structure et la qualité des données RH ;
- Fusionner plusieurs sources de données ;
- Nettoyer et transformer les variables ;
- Construire un modèle de classification binaire ;
- Optimiser le seuil de décision afin de maximiser le compromis précision/rappel ;
- Interpréter les résultats avec des méthodes explicables (SHAP, importance des variables).

## Structure du projet

```text
Projet4Rendu/
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── Data/
│   ├── extrait_eval.csv
│   ├── extrait_sirh.csv
│   └── extrait_sondage.csv
├── dataScientistTechNova.ipynb
└── profiling_*.html
```

## Données

Le projet s’appuie sur 3 jeux de données :

- `extrait_sondage.csv` : informations collectées via le sondage RH, notamment les variables liées à l’engagement, à la satisfaction et au profil du salarié ;
- `extrait_sirh.csv` : données de ressources humaines et de gestion des employés ;
- `extrait_eval.csv` : données liées aux évaluations et aux performances.

La cible est :

```text
a_quitte_l_entreprise
```

avec une variable binaire :

- `Non` : le salarié est resté
- `Oui` : le salarié a quitté l’entreprise

## Installation

Ce projet utilise `uv` pour gérer l’environnement Python et les dépendances.

### Prérequis

- Python >= 3.13
- uv installé sur votre machine

### Installation du projet

Depuis la racine du projet :

```bash
cd /Users/samuelgabbai/Documents/workspaceIT/formation_datascientist/Projet4Rendu
uv sync
```

### Ajouter ou mettre à jour une dépendance

```bash
uv add nom_du_paquet
```

ou

```bash
uv lock --upgrade
uv sync
```

## Usage

### Lancer le notebook

```bash
cd /Users/samuelgabbai/Documents/workspaceIT/formation_datascientist/Projet4Rendu
uv run jupyter notebook
```

ou ouvrir directement :

```text
dataScientistTechNova.ipynb
```

dans VS Code / Jupyter.

### Vérifier les dépendances

```bash
uv pip list
```

### Lancer l'API de prédiction

Après avoir exécuté le notebook jusqu'à la cellule d'export, le modèle calibré et son seuil sont
enregistrés dans `artifacts/turnover_model.joblib`.

```bash
uv sync --extra api
uv run uvicorn api:app --reload
```

La documentation interactive est disponible sur <http://127.0.0.1:8000/docs>. L'API expose
`GET /health`, `GET /features`, `POST /predict` et `GET /employees/{employee_id}/score`.
La route par ID renvoie le score d'un salarié présent dans les sources du notebook, par exemple
`GET /employees/1001/score`. `POST /predict` attend, sous `features`, les variables numériques
déjà préparées et encodées ; `GET /features` fournit leurs noms exacts. Les résultats incluent la
probabilité estimée, le seuil optimisé et la décision. Le chemin de l'artefact peut être remplacé
avec la variable `HRNOVA_MODEL_PATH`.

## Méthodologie

Le projet suit une logique de data science structurée :

1. Analyse exploratoire des datasets
2. Contrôle de qualité des données
3. Nettoyage et fusion des tables
4. Encodage et feature engineering
5. Préparation du jeu d’entraînement / test
6. Comparaison de plusieurs modèles
7. Optimisation du Random Forest
8. Calibration des probabilités
9. Ajustement du seuil de décision
10. Interprétation globale et locale avec SHAP

## Modèle retenu

Le modèle principal est un Random Forest, calibré à l’aide de `CalibratedClassifierCV`, puis évalué avec un seuil optimisé selon le F1 de la classe minoritaire.

Les modèles comparés incluent notamment :

- DummyClassifier
- LogisticRegression
- RandomForest
- LightGBM
- RandomForest + SMOTE

## Interprétabilité

Une partie importante du projet porte sur l’explicabilité du modèle :

- importance native du modèle ;
- importance par permutation ;
- SHAP Beeswarm Plot ;
- SHAP Waterfall Plot local pour des salariés spécifiques.

Cela permet d’expliquer non seulement le score global du modèle, mais aussi les facteurs qui poussent un salarié vers un risque de départ.

## Résultats attendus

Le projet vise à obtenir un modèle capable de :

- détecter les salariés à risque de départ avec un bon rappel ;
- conserver une précision opérationnelle suffisante ;
- exploiter un seuil de décision mieux adapté à la cible minoritaire ;
- fournir des éléments interprétables pour les décideurs RH.

## Limites et améliorations possibles

- Ajouter de nouvelles sources de données métier (absentéisme, mobilité, historique salariale, etc.) ;
- Tester d’autres modèles ou hyperparamètres ;
- Utiliser un pipeline de validation plus robuste ;
- Mettre en place un monitoring si le modèle doit être déployé ;
- Comparer plusieurs seuils selon les coûts métier (fausses négatives vs fausses positives).

## Auteur

Samuel GABBAI
Projet réalisé dans le cadre du projet 4 de la formation Data Scientist.


---

