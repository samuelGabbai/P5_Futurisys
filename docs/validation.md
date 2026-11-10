# Recette et preuves de validation

Cette page décrit les corrections des six points identifiés lors de l’audit initial.
Les preuves sont des exécutions locales avec le modèle réel et PostgreSQL, ou des
tests isolés explicitement distingués des étapes à exécuter dans GitHub.

| Point | Correction livrée | Vérification |
| --- | --- | --- |
| Dépôt Git | Artefacts générés retirés de l’index sans suppression locale, `.editorconfig`, conventions de branches/commits et modèle de PR | `CONTRIBUTING.md`, `.gitignore` et état Git |
| Pipeline YAML | Sources Docker réintégrées, construction et contrôle HTTP de l’image obligatoires dans le job principal | Test du contexte de construction ; vrai build et contrôle configurés sur le runner Linux |
| Authentification et rôles | Initialisation locale idempotente avec secrets aléatoires, séparation des rôles, appels de validation authentifiés | Contrôle HTTP réel et tests 401/403, comptes désactivés, isolation des droits |
| Tests | Contraintes SQLite activées, tests supplémentaires des outils et vues, exécution dans une base PostgreSQL jetable, couverture élargie | Rapports Pytest, JUnit et couverture ; aucun test PostgreSQL ignoré dans la recette finale |
| Besoins analytiques | Utilisateurs, finalités, KPI, sources, accès, fréquence et critères de recette définis ; deux vues SQL | [Spécification analytique](analytics.md) et tests PostgreSQL des agrégats |
| Performances et volumes | Limites de lignes/colonnes et benchmark HTTP reproductible | [Mesures](performance.md), rapport JSON, tests des frontières de volume |

## Validation du service local

PostgreSQL est lancé sur `127.0.0.1:5433` et FastAPI sur `127.0.0.1:8000` pendant
la recette. Les comptes locaux sont initialisés sans exposer les mots de passe.

```bash
uv run --no-sync python scripts/local_postgres.py start
uv run --no-sync python scripts/manage_users.py --bootstrap-local
uv run --no-sync uvicorn api:app --host 127.0.0.1 --port 8000
```

Dans un autre terminal :

```bash
uv run --no-sync python scripts/smoke_container.py --base-url http://127.0.0.1:8000
uv run --no-sync python scripts/verify_database.py
```

Le contrôle HTTP réel vérifie la connexion, une prédiction, le téléchargement du
modèle avec le livreur et les refus d’accès croisés. Le [rapport BDD](database_validation.json)
confirme les 1 470 lignes par source, la conservation des valeurs, les cinq routes
d’inférence, la concordance des réponses avec les sorties stockées et les droits
limités du rôle SQL applicatif. Les appels de vérification ajoutent des traces.

## Tests et couverture

```bash
uv run --no-sync pytest
uv run --no-sync python scripts/run_postgres_tests.py \
  --cov-report=xml --cov-report=json:reports/coverage.json --junitxml=reports/junit.xml
```

La première commande utilise SQLite si `TEST_DATABASE_URL` n’est pas défini ; ses
clés étrangères sont maintenant activées. Les cas PostgreSQL doivent être ignorés
sur SQLite, car les opérateurs JSONB et la création de base ne sont pas équivalents.

La seconde utilise le serveur PostgreSQL local avec les identifiants protégés de
`.local/admin.env`. Elle crée une base au nom aléatoire, y exécute la suite, puis
la supprime même si les tests échouent. Elle ne vide pas la base `hrnova`.

La couverture porte maintenant sur les huit modules applicatifs **et les scripts
opérationnels**. Les générateurs de présentations `scripts/build_*.py` sont exclus.
Le seuil CI est **95 % sur ce périmètre élargi**, au lieu de 100 % sur six modules
seulement. Les fichiers JUnit, XML, JSON et HTML sont produits dans `reports/`,
`coverage.xml` et `htmlcov/`, ignorés par Git et conservés comme artefacts CI.
La recette du 2026-11-10 donne **263 tests PostgreSQL réussis, zéro
échec et zéro test ignoré**, avec **100 % de couverture des lignes** :
1 273 lignes exécutées sur 1 273, sans réduction du périmètre ni nouvelles exclusions.
Les 24 cas supplémentaires vérifient les exports invalides, la construction du client
Hugging Face, les commandes Docker et leur CLI, les configurations manquantes,
l’attente de disponibilité, la confirmation de mot de passe et la lecture des droits SQL.
Les frontières externes sont simulées avec des mocks ; aucun upload ni déploiement
distant n’est exécuté par ces tests. La couverture des branches n’est pas activée.
Le seuil CI demeure 95 % ; le résultat mesuré est 100 %.
Le [résultat de recette](test_results.json) en conserve la synthèse.

## Limites de la validation

Docker n’est pas installé sur la machine de recette. Son contexte est vérifié par
test, et la CI contient un vrai build puis un contrôle du conteneur avec PostgreSQL.
Cette étape doit être confirmée par une exécution GitHub Actions après push : une
configuration YAML ne constitue pas une preuve d’exécution distante.

Les secrets, runners, approbations et protections de branches de GitHub doivent
être configurés dans le dépôt cible. Aucun secret distant n’a été modifié et aucun
modèle n’a été publié lors de cette recette. Le cloud reste facultatif ; une API
locale fonctionnelle est la cible démontrée ici.
