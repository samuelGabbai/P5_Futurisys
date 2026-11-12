# Démarrer de zéro

Cette page suit le chemin le plus court, du dépôt Git à une API utilisable **en local**. Toutes les commandes se lancent dans un terminal, dans l’ordre.

## 1. Préparer la machine

Installer [Git](https://git-scm.com/downloads), [uv](https://docs.astral.sh/uv/getting-started/installation/) et PostgreSQL 18. Python 3.13 est recommandé : c’est la version utilisée par la CI. Vérifier les outils :

```bash
git --version
uv --version
```

Sur le Mac de développement, PostgreSQL 18 est installé dans `/Library/PostgreSQL/18/bin`. Pour une autre installation, préciser le chemin de ses binaires à l’étape 3. Le [guide d’installation complet](installation.md) explique aussi la connexion à un serveur PostgreSQL existant.

## 2. Récupérer le projet et installer ses dépendances

```bash
git clone https://github.com/samuelGabbai/P5_Futurisys.git
cd P5_Futurisys
uv sync --locked --python 3.13 --extra api --extra dev --extra docs
```

Le dépôt contient le modèle entraîné dans `artifacts/` et les trois CSV dans `Data/`. `uv.lock` fixe les versions installées.

## 3. Créer et démarrer la base locale

```bash
uv run --no-sync python scripts/local_postgres.py start
```

Ce script initialise PostgreSQL, crée la base `hrnova`, importe les données et applique les migrations. Il utilise **127.0.0.1:5433**. Si PostgreSQL est installé ailleurs :

```bash
uv run --no-sync python scripts/local_postgres.py start --pg-bin /chemin/vers/postgresql/bin
```

Le script crée les secrets locaux dans `.env` et `.local/admin.env`. Un nouveau `start` conserve l’historique des échanges. Pour vérifier l’état :

```bash
uv run --no-sync python scripts/local_postgres.py status
```

## 4. Créer les comptes locaux

```bash
uv run --no-sync python scripts/manage_users.py --bootstrap-local
```

Trois comptes sont créés sur une configuration vierge : `application` (**utilisateur**), `livraison` (**livreur**) et `admin`. Les mots de passe aléatoires sont enregistrés dans `.local/api-credentials.env` ; ce fichier reste sur la machine et n’est pas suivi par Git. La commande préserve les comptes déjà présents.

## 5. Lancer l’API

```bash
uv run --no-sync uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Garder ce terminal ouvert. Vérifier que l’API répond :

```bash
curl http://127.0.0.1:8000/health
```

La réponse attendue est `{"status":"ok"}`. Ouvrir **[Swagger](http://127.0.0.1:8000/docs)**, cliquer sur **Authorize**, saisir le compte `application` et son mot de passe trouvé dans `.local/api-credentials.env`. Appeler `GET /auth/me` pour vérifier le rôle, puis essayer `GET /features` ou `POST /predict`. Les [exemples d’appels](api.md) utilisent les fichiers `examples/`.

## 6. Ouvrir cette documentation

Dans un **autre terminal**, depuis `P5_Futurisys` :

```bash
uv run --no-sync mkdocs serve
```

Ouvrir **[MkDocs](http://127.0.0.1:8001)**. Le port `8001` est réservé à la documentation ; l’API écoute sur `8000`.

!!! tip "Au prochain démarrage"
    Revenir dans le dépôt, relancer `uv run --no-sync python scripts/local_postgres.py start`, puis la commande Uvicorn de l’étape 5. Les comptes locaux sont conservés.

Pour les variables d’environnement, les tests et les autres plateformes, consulter [l’installation complète](installation.md). Le [dépôt GitHub](https://github.com/samuelGabbai/P5_Futurisys) contient le code source et l’historique.
