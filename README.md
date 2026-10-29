# HRNova — Prédiction du départ des salariés

HRNova estime le risque de départ d'un salarié dans le cas d'étude TechNova Partners.
Le projet associe un modèle scikit-learn calibré, une API FastAPI validée avec
Pydantic et une base PostgreSQL qui conserve les entrées, sorties et échanges API.

L'API attend des variables numériques **déjà préparées et encodées**. Le notebook
réalise la préparation, l'entraînement et l'évaluation ; il ne s'exécute pas à chaque
requête ni automatiquement à chaque push.

## Documentation

| Besoin | Guide |
| --- | --- |
| Vue d'ensemble et parcours utilisateur | [Accueil](docs/index.md) |
| Installer et configurer le projet | [Installation](docs/installation.md) |
| Endpoints, Swagger, JSON/CSV et exemples Python | [Référence API](docs/api.md) |
| Contraintes Pydantic et tests de chaque endpoint | [Validation](docs/api_validation.md) |
| Données, choix du modèle, performances et limites | [Fiche modèle](docs/model.md) |
| Signification des 43 variables | [Contrat d'entrée](docs/features.md) |
| Composants et choix techniques | [Architecture](docs/architecture.md) |
| Schéma relationnel, import et traçabilité | [PostgreSQL](docs/database.md) |
| Logs lisibles dans DBeaver | [Logs API](docs/api_logs.md) |
| Environnements, CI/CD et lancement du service | [Déploiement](docs/deployment.md) |
| Publication automatique dans SamGabb/hrnova | [Hugging Face](docs/huggingface.md) |
| Mises à jour, sauvegardes, retour arrière et diagnostic | [Maintenance](docs/maintenance.md) |

Les guides sont consultables directement dans GitHub. Pour ouvrir la documentation
MkDocs avec recherche et diagrammes :

```bash
uv sync --locked --extra api --extra dev --extra docs
uv run --no-sync mkdocs serve
```

Documentation : **http://127.0.0.1:8001**. Ce port est distinct de celui de l'API.

## Démarrage rapide

Prérequis : Git, uv, Python **3.13 recommandé** et PostgreSQL **18**.
Le package déclare Python >= 3.10 ; la CI vérifie actuellement Python 3.13.

```bash
git clone https://github.com/samuelGabbai/P5_Futurisys.git
cd P5_Futurisys
uv sync --locked --python 3.13 --extra api --extra dev
uv run --no-sync python scripts/local_postgres.py start
uv run --no-sync uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Le script PostgreSQL utilise par défaut les binaires Mac dans
`/Library/PostgreSQL/18/bin`. Sur une autre installation, ajouter
`--pg-bin /chemin/vers/postgresql/bin`, ou suivre le guide pour un serveur
PostgreSQL existant.

L'instance locale utilise la base **hrnova**, l'hôte **127.0.0.1**, le port **5433**
et le rôle applicatif **hrnova_app**. Les identifiants sont générés dans `.env`
et `.local/admin.env`, ignorés par Git. Les sources et l'artefact complet sont
importés sans supprimer l'historique d'une base existante.

Swagger : **http://127.0.0.1:8000/docs** · ReDoc : **http://127.0.0.1:8000/redoc**.

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/employees/1/score
```

L'API refuse une inférence si la BDD n'est pas disponible. Après un redémarrage
du Mac, relancer PostgreSQL avec le script `start`.

## Utiliser l'API

| Endpoint | Fonction |
| --- | --- |
| `GET /health` | Vérifier la disponibilité locale et le chargement du modèle |
| `GET /features` | Obtenir les noms exacts des variables attendues |
| `POST /predict` | Prédiction JSON au seuil optimisé |
| `POST /predict/file` | Classes natives pour un fichier CSV |
| `POST /predict-proba/file` | Probabilités par classe pour un CSV |
| `POST /score/file` | Accuracy native et métriques au seuil optimisé, avec vraies réponses |
| `GET /employees/{employee_id}/score` | Score au seuil optimisé à partir des variables en BDD |

Des exemples synthétiques complets sont fournis dans `examples/` :

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' --data-binary @examples/predict.json

curl -X POST http://127.0.0.1:8000/predict-proba/file \
  -F 'file=@examples/employees.csv'

curl -X POST http://127.0.0.1:8000/score/file \
  -F 'file=@examples/employees_with_target.csv'
```

Les fichiers doivent être UTF-8, numériques et limités à 10 Mio. La cible réelle
est nécessaire uniquement pour le score. Les exemples contiennent des profils
et des cibles fictifs ; ils démontrent le contrat, pas les performances.

Le seuil optimisé diffère de la règle native de `model.predict` : les routes JSON
et par ID peuvent donc produire une décision différente de `/predict/file`.
Les erreurs, formats et conventions sont détaillés dans [la référence API](docs/api.md).

## Données et résultats du modèle

Les sources `Data/extrait_sirh.csv`, `Data/extrait_sondage.csv` et
`Data/extrait_eval.csv` comportent chacune **1 470 lignes**. La cible
`a_quitte_l_entreprise` contient 1 233 `Non` (0) et 237 `Oui` (1).

Le modèle publié est un **Random Forest calibré par méthode sigmoid**,
avec 43 variables et un seuil optimisé de **0,2231813754**.
Le notebook utilise 1 176 lignes d'entraînement et 294 de test, stratifiées.

Résultats enregistrés dans le notebook, cellule 41, examinés le 27 octobre 2026 :

| Métrique de test | Seuil optimisé |
| --- | --- |
| Accuracy | 0,8027 |
| Précision | 0,4203 |
| Rappel | 0,6170 |
| F1 | 0,5000 |
| ROC-AUC | 0,7692 |

Ces résultats ne sont pas une mesure de production. Le prétraitement actuel ajuste
certaines références avant le split train/test ; cette limite peut influencer
l'évaluation. La [fiche modèle](docs/model.md) détaille la comparaison avec les
baselines, la calibration, les limites et les améliorations nécessaires.

Pour travailler sur le notebook :

```bash
uv sync --locked --extra api --extra dev --extra notebook
uv run --no-sync jupyter lab dataScientistTechNova.ipynb
```

## Traçabilité et configuration

Chaque requête reçoit un `X-Request-ID`. Le service enregistre puis relit les
inputs avant le calcul et les outputs avant la réponse. La vue `public.api_logs`
regroupe messages, durées, étapes et erreurs ; les tables dédiées conservent
les données et le hash du modèle. Les incidents initiaux de BDD restent dans les
logs du processus, et un arrêt brutal peut laisser une requête `pending`.

`DATABASE_URL` configure PostgreSQL et `HRNOVA_MODEL_PATH` le fichier de modèle.
La liste complète des variables et des droits se trouve dans
[la configuration](docs/installation.md#variables-de-configuration).
L'API est conçue pour l'usage local et n'a pas d'authentification HTTP.

## Tests, documentation et déploiement

```bash
uv sync --locked --extra api --extra dev --extra docs
uv run --no-sync pytest --cov-report=xml --junitxml=reports/junit.xml
uv run --no-sync python scripts/export_openapi.py
uv run --no-sync mkdocs build --strict
uv build
```

Le workflow GitHub Actions lance les tests avec PostgreSQL à chaque push et PR,
construit la documentation et le package et prépare l'export du modèle.
Configurer la protection des branches avec le contrôle **Validation avant fusion**
pour bloquer effectivement les fusions si les vérifications échouent.

Les push sur `main` publient ensuite le modèle vers
[SamGabb/hrnova](https://huggingface.co/SamGabb/hrnova), après validation de
l'environnement `production`. Le secret GitHub `HF_TOKEN` doit autoriser l'écriture ;
`HF_REPO_ID` peut remplacer le dépôt cible. Aucun secret Hugging Face n'est requis
pour les tests ou la documentation. L'export exclut le dictionnaire des salariés.

Les environnements `development`, `staging` et `production` séparent les validations,
secrets et déploiements. Le déploiement Docker de l'API est disponible sur les
branches `development`, `develop` et `main`, après activation de la variable GitHub
`ENABLE_API_DEPLOYMENT=true` et configuration de runners dédiés. Le script vérifie
la base et le modèle, démarre l'API et teste une prédiction tracée ; en cas d'échec,
il tente de restaurer l'image précédente. Les bases PostgreSQL sont provisionnées
et initialisées séparément. Les configurations et commandes sont dans
[le guide de déploiement](docs/deployment.md#activer-le-deploiement-api-dans-github-actions).
Le déploiement n'est pas activé dans GitHub par la modification des fichiers locaux.

## Structure du dépôt

```text
P5_Futurisys/
├── api.py / schemas.py       # Routes et contrats Pydantic
├── inference.py / audit.py   # Inférences tracées et journal HTTP
├── database.py / create_db.py
├── Data/                    # Trois sources CSV
├── artifacts/               # Artefact complet de confiance
├── dataScientistTechNova.ipynb
├── scripts/                 # PostgreSQL, vérification, OpenAPI, publication
├── tests/
├── examples/                # JSON et CSV synthétiques
├── docs/ / mkdocs.yml        # Guides, schémas et performances
├── .github/workflows/ci.yml
└── pyproject.toml / uv.lock
```

## Maintenance et contribution

À chaque mise à jour du modèle, conserver le commit, les métriques et le hash,
réimporter les variables préparées puis redémarrer l'API. Le protocole de revue
mensuelle, d'évaluation trimestrielle et de retour arrière est décrit dans
[la maintenance](docs/maintenance.md).

Pour une modification : créer une branche, mettre à jour tests et documentation,
exécuter les vérifications puis ouvrir une PR. Signaler un problème dans
[les issues](https://github.com/samuelGabbai/P5_Futurisys/issues) avec le message
d'erreur et le `X-Request-ID`, sans mot de passe, token ou données RH.

Auteur : **Samuel Gabbai** — cas d'étude Data Science TechNova Partners.

