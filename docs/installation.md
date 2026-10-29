# Installation et configuration

## Prérequis

- Git et `uv` pour récupérer le dépôt et respecter `uv.lock`.
- Python 3.13 recommandé : c'est la version utilisée en CI. Le package déclare
  Python `>=3.10`, mais la pipeline actuelle ne teste pas toutes ces versions.
- PostgreSQL 18 pour reproduire l'environnement local et la CI.
- L'artefact complet `artifacts/turnover_model.joblib` et les trois CSV de `Data/`.

```bash
git clone https://github.com/samuelGabbai/P5_Futurisys.git
cd P5_Futurisys
uv sync --locked --python 3.13 --extra api --extra dev
```

Les commandes suivantes sont exécutées depuis la racine du dépôt. `uv sync` est
exact : préciser ensemble les extras à conserver lors d'une synchronisation.
Par exemple, pour travailler aussi sur les notebooks et la documentation :

```bash
uv sync --locked --extra api --extra dev --extra notebook --extra docs
```

## PostgreSQL dédié au projet

Sur le Mac ayant servi au développement, les binaires sont dans
`/Library/PostgreSQL/18/bin` :

```bash
uv run --no-sync python scripts/local_postgres.py start
```

Sur une autre installation, donner le dossier contenant `initdb`, `pg_ctl` et `pg_dump` :

```bash
uv run --no-sync python scripts/local_postgres.py start --pg-bin /chemin/postgresql/bin
```

Exécuter le script avec le compte utilisateur habituel, pas avec `root`.
Il initialise une instance dans `.local/postgres`, écoute sur `127.0.0.1:5433`,
crée la base `hrnova`, importe les sources et applique les migrations SQL disponibles.
Il génère `.env` avec le rôle applicatif `hrnova_app`, et `.local/admin.env` avec
les identifiants d'administration. Les mots de passe ne sont pas affichés.
Un `start` sur une instance existante réimporte les données sans effacer l'historique.

Le [guide PostgreSQL](database.md) décrit aussi l'installation sur un serveur déjà
existant, les droits des deux rôles et la recréation avec sauvegarde.

## Variables de configuration

| Variable | Utilisation | Valeur ou format |
| --- | --- | --- |
| `DATABASE_URL` | Connexion utilisée par l'API et par défaut par l'import | `postgresql+psycopg://UTILISATEUR:MOT_DE_PASSE@127.0.0.1:5433/hrnova` |
| `DATABASE_ADMIN_URL` | Connexion de création de base, pour `create_db.py --create-database` | URL vers `postgres` avec droit `CREATEDB` ; facultative si le rôle de `DATABASE_URL` possède ce droit |
| `HRNOVA_MODEL_PATH` | Fichier du modèle local | `artifacts/turnover_model.joblib` ; chemin absolu recommandé hors racine du dépôt |
| `TEST_DATABASE_URL` | Connexion des tests PostgreSQL | Base dédiée et rôle autorisé à créer/supprimer des schémas de test |
| `HF_TOKEN` | Secret du job de publication | Token à droit d'écriture, conservé dans les secrets GitHub |
| `HF_REPO_ID` | Dépôt Model cible | Facultatif, `SamGabb/hrnova` par défaut |

L'API charge `.env` avec `python-dotenv`, sans remplacer les variables déjà définies
dans l'environnement du processus. Les variables de publication doivent être configurées
dans GitHub Actions ou dans l'environnement du terminal ; le script de publication
ne charge pas automatiquement `.env`.

Pour un serveur PostgreSQL existant, partir de
[`.env.example`](https://github.com/samuelGabbai/P5_Futurisys/blob/main/.env.example).
Le rôle utilisé pour créer les tables et importer les données doit avoir les droits
correspondants. Après l'import, l'API doit utiliser le rôle applicatif limité.
Ne pas committer les secrets, les fichiers `.env` ou le répertoire `.local`.

## Lancer l'API

```bash
uv run --no-sync uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Vérifier le service et la disponibilité du modèle :

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/features
```

La réponse de santé attendue est `{"status":"ok"}`. L'API refuse de commencer un
calcul si PostgreSQL est inaccessible. Le journal étant lui-même stocké en BDD,
la consultation de Swagger et d'OpenAPI requiert aussi une BDD disponible.

## Notebook et vérifications

```bash
uv sync --locked --extra api --extra dev --extra notebook
uv run --no-sync jupyter lab dataScientistTechNova.ipynb
uv run --no-sync pytest --cov-report=xml --junitxml=reports/junit.xml
```

Le script suivant vérifie l'intégrité des sources importées et les cinq routes
d'inférence avec le modèle réel ; il ajoute des échanges tracés à la BDD :

```bash
uv run --no-sync python scripts/verify_database.py
```

En cas d'erreur, consulter [le diagnostic](maintenance.md#diagnostic-des-problemes-courants).
