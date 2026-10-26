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
- [Base PostgreSQL et traçabilité](#base-postgresql-et-traçabilité)
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
uv run --no-sync python scripts/local_postgres.py start
uv run uvicorn api:app --reload
```

La documentation interactive est disponible sur <http://127.0.0.1:8000/docs>. L'API expose
`GET /health`, `GET /features`, `POST /predict` et `GET /employees/{employee_id}/score`.
La route par ID renvoie le score d'un salarié présent dans les sources du notebook, par exemple
`GET /employees/1001/score`. `POST /predict` attend, sous `features`, les variables numériques
déjà préparées et encodées ; `GET /features` fournit leurs noms exacts. Les résultats incluent la
probabilité estimée, le seuil optimisé et la décision. Le chemin de l'artefact peut être remplacé
avec la variable `HRNOVA_MODEL_PATH`.

### Envoyer un CSV : predict, predict_proba et score

Les trois routes acceptent un fichier via le champ multipart `file` :

| Route POST | Contenu du CSV | Résultat |
| --- | --- | --- |
| `/predict/file` | Variables du modèle | Classes prédites avec `model.predict` |
| `/predict-proba/file` | Variables du modèle | Probabilités avec `model.predict_proba` et ordre des classes |
| `/score/file` | Variables et vraies réponses | Accuracy avec `model.score`, puis accuracy, précision, rappel et F1 au seuil optimisé |

Lancer l'API puis ouvrir <http://127.0.0.1:8000/docs>. Dans **Fichiers CSV**, sélectionner
une route, cliquer sur **Try it out**, choisir le fichier et cliquer sur **Execute**.

```bash
uv sync --locked --extra api
uv run --no-sync python scripts/local_postgres.py start
uv run --no-sync uvicorn api:app --reload
```

Le fichier doit être un **CSV UTF-8**, avec une ligne d'en-tête et au moins une ligne de données,
limité à 10 Mio. Les noms des colonnes doivent correspondre exactement à `GET /features`.
Leur ordre est libre. Les variables doivent être numériques, déjà préparées et encodées,
sans valeur manquante ou infinie. Les CSV RH bruts du dossier `Data/` doivent donc passer
par la préparation du notebook avant leur envoi. Ne pas ajouter de colonne d'identifiant.
Les résultats suivent l'ordre des lignes du fichier.

Pour `/score/file`, ajouter la colonne `a_quitte_l_entreprise` avec les réponses réelles
(`0`/`1` ou `Non`/`Oui`). Un autre nom est possible avec `?target_column=nom_colonne`.
Pour un CSV séparé par des points-virgules, ajouter `?separator=%3B`.

```bash
curl -X POST http://127.0.0.1:8000/predict/file \
  -F 'file=@employes_prepares.csv'

curl -X POST http://127.0.0.1:8000/predict-proba/file \
  -F 'file=@employes_prepares.csv'

curl -X POST http://127.0.0.1:8000/score/file \
  -F 'file=@employes_prepares_avec_cible.csv'
```

`predictions` contient une classe par ligne. Dans `probabilities`, chaque ligne contient
les probabilités dans l'ordre du tableau `classes`. Le champ `score` mesure la proportion
de bonnes prédictions natives. Les champs `threshold_*` évaluent la décision au seuil
optimisé du notebook ; ils peuvent différer du score natif. La route JSON `/predict`
existante continue à utiliser ce seuil optimisé.

L'envoi de fichiers utilise [UploadFile de FastAPI](https://fastapi.tiangolo.com/tutorial/request-files/).
La définition du score suit celle du [modèle calibré scikit-learn](https://scikit-learn.org/1.7/modules/generated/sklearn.calibration.CalibratedClassifierCV.html).

## Base PostgreSQL et traçabilité

Les [logs API détaillés](docs/api_logs.md) sont consultables dans DBeaver via la vue
`public.api_logs` : message, durée, fichier, nombre de lignes, étape atteinte et cause des erreurs.

L'API utilise obligatoirement PostgreSQL pour enregistrer puis relire chaque entrée
du modèle et chaque résultat. La base locale `hrnova` contient les trois CSV complets,
les variables préparées et les journaux d'échanges. Chaque réponse porte un en-tête
`X-Request-ID` permettant de retrouver ses inputs et outputs. Sans BDD, l'API renvoie 503.

Le [guide PostgreSQL](docs/database.md) contient le schéma relationnel, les commandes
de création/import, les droits d'accès et les exemples SQL. Le script
[`create_db.py`](create_db.py) réalise l'import transactionnel et idempotent ;
[`scripts/local_postgres.py`](scripts/local_postgres.py) provisionne une instance locale
avec des rôles distincts d'administration et d'application.

## Intégration continue (GitHub Actions)

La pipeline prépare aussi un export du modèle pour Hugging Face. Après un push sur
`main` et la réussite des vérifications, le job de publication l'envoie vers le dépôt
Model `SamGabb/hrnova`, avec le secret GitHub `HF_TOKEN`. La variable facultative
`HF_REPO_ID` permet de changer de dépôt. Le [guide Hugging Face](docs/huggingface.md) détaille
la configuration, les fichiers publiés et la mise à jour du modèle.

Le workflow `.github/workflows/ci.yml` s'exécute à chaque push, à chaque pull request
et manuellement depuis l'onglet **Actions** de GitHub. Il utilise Python 3.13 et installe
les dépendances avec `uv sync --locked --extra api --extra dev` pour respecter `uv.lock`.

Il exécute les tests de l'API avec mesure de couverture, puis construit le package Python
(wheel et archive source). Les rapports de tests et de couverture ainsi que le package
sont téléchargeables dans les artefacts de l'exécution pendant 14 jours.
Les tests utilisent un modèle simulé et ne nécessitent pas de réentraîner le notebook.
La CI démarre également PostgreSQL 18 pour vérifier l'import du dataset complet et
la traçabilité, dans des schémas isolés supprimés après chaque test.
Aucun secret n'est nécessaire ; ce workflow ne déploie pas l'API.

### Tests automatiques et validation avant fusion

Chaque push vers n'importe quelle branche déclenche les tests. Un commit uniquement local
ne déclenche pas GitHub Actions : il est vérifié lorsqu'il est poussé sur GitHub.
Les pull requests déclenchent aussi les tests sur le résultat de la fusion proposée.
L'événement `merge_group` prend en charge une éventuelle file de fusion GitHub.
Le contrôle **Validation avant fusion** échoue si les tests ou la construction échouent.

Pour bloquer effectivement les fusions, après une première exécution du workflow,
configurer une protection pour `main` et `develop` dans **Settings → Branches**
(ou un ruleset dans **Settings → Rules → Rulesets**) :

1. Exiger une pull request avant fusion (**Require a pull request before merging**).
2. Exiger les contrôles réussis (**Require status checks to pass before merging**)
   et sélectionner **Validation avant fusion**.
3. Exiger une branche à jour (**Require branches to be up to date before merging**).
4. Appliquer les règles aux administrateurs et éviter les autorisations de contournement.

Ces paramètres sont des réglages du dépôt GitHub ; le fichier YAML seul ne peut pas
interdire une fusion. Ils restent à activer sur le dépôt.

### Gestion des environnements

Après une CI réussie, les push et lancements manuels exécutent un job supplémentaire
dans l'environnement GitHub correspondant à la branche :

| Branche | Environnement GitHub | Usage |
| --- | --- | --- |
| Branches de travail | `development` | Validation pendant le développement |
| `develop` | `staging` | Validation avant production |
| `main` | `production` | Validation de la version principale |

Dans **Settings → Environments**, créer ces trois environnements. Limiter `staging`
à la branche `develop` et `production` à `main` avec les règles de branches autorisées.
Pour `production`, ajouter un approbateur obligatoire si cette option est disponible
pour le dépôt. Laisser `development` accessible aux branches de travail.

Chaque environnement peut définir la variable **HRNOVA_MODEL_PATH**, utilisée par
l'API pour choisir son modèle. Sans valeur spécifique, le workflow utilise
`artifacts/turnover_model.joblib`. Les futurs identifiants de services doivent être
enregistrés dans les **secrets de l'environnement** concerné.

Le job vérifie que le chemin configuré est non vide et se termine par `.joblib`, puis
relance les tests avec cette configuration. Les tests utilisent un modèle simulé :
ils ne valident ni la présence ni la qualité d'un modèle réel. Aucun serveur n'est
déployé par ce workflow. Les pull requests exécutent la CI sans accéder aux
environnements cibles, afin que leurs contrôles n'attendent pas une approbation de production.

Références : [protection des branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
et [environnements GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

Pour reproduire les vérifications localement :

```bash
uv sync --locked --extra api --extra dev
uv run --no-sync pytest --cov-report=xml --junitxml=reports/junit.xml
uv build
```

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

