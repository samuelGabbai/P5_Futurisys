# PostgreSQL et traçabilité du modèle

Le dataset complet est conservé dans trois tables relationnelles. Les identifiants
`id_employee`, `code_sondage` (par exemple `000001`) et `eval_number` (`E_1`) sont
rapprochés comme dans le notebook, sans perdre leur représentation source.
Les 1 470 lignes de chaque CSV sont importées ; aucun échantillonnage n'est effectué.

## Schéma relationnel

```mermaid
erDiagram
    employees ||--|| surveys : "employee_id"
    employees ||--|| evaluations : "employee_id"
    employees ||--o{ prepared_employees : "employee_id"
    model_versions ||--o{ prepared_employees : "model_sha256"
    model_versions |o--o{ api_exchanges : "model_sha256"
    api_exchanges ||--o{ model_inputs : "exchange_id"
    employees |o--o{ model_inputs : "employee_id"
    api_exchanges ||--o| model_outputs : "exchange_id"
    employees {
        int id_employee PK
        int age
        int revenu_mensuel
        string departement
        string poste
    }
    surveys {
        int employee_id PK,FK
        string code_sondage UK
        string a_quitte_l_entreprise
    }
    evaluations {
        int employee_id PK,FK
        string eval_number UK
    }
    model_versions {
        string sha256 PK
        jsonb feature_names
        float threshold
        int positive_class
    }
    prepared_employees {
        int employee_id PK,FK
        string model_sha256 PK,FK
        jsonb features
    }
    api_exchanges {
        string id PK
        string endpoint
        string method
        string status
        int http_status
        datetime started_at
        datetime completed_at
        string model_sha256 FK
        string operation
        string filename
        string error_type
        float duration_ms
        string message
        string processing_stage
        int row_count
        int feature_count
        jsonb request_details
        jsonb error_details
        jsonb response_summary
    }
    model_inputs {
        int id PK
        string exchange_id FK
        int row_index
        int employee_id FK
        jsonb features
        int target
    }
    model_outputs {
        string exchange_id PK,FK
        jsonb payload
        jsonb model_values
        datetime created_at
    }
```

Le diagramme abrège les colonnes métier : le schéma SQL complet se trouve dans
[`schema.sql`](schema.sql) et les classes ORM dans [`database.py`](../database.py).
Les colonnes métier sont typées et non nulles. Les clés étrangères garantissent
les liens entre sources. Un couple `(exchange_id, row_index)` ne peut pas être dupliqué.
Les index portent sur les dates, routes, statuts et identifiants de requêtes.
JSONB conserve les variables numériques, dont la liste dépend de la version du modèle,
et les sorties structurées. L'ordre des lignes est fixé par `row_index` (à partir de zéro).

## Créer et alimenter la base locale

Prérequis : PostgreSQL installé et les dépendances API disponibles :

```bash
uv sync --locked --extra api --extra dev
```

Sur cette machine, PostgreSQL 18 se trouve dans `/Library/PostgreSQL/18/bin`.
Le script suivant initialise une instance dédiée, démarre le serveur et importe les données :

```bash
uv run --no-sync python scripts/local_postgres.py start
```

Il utilise `127.0.0.1:5433`, la base `hrnova`, et le dossier `.local/postgres`.
Il ne modifie pas les autres instances PostgreSQL. Des mots de passe aléatoires sont
générés ; la configuration de l'API est enregistrée dans `.env`, celle de
l'administrateur dans `.local/admin.env`, avec permissions de fichier `0600`.
Ces fichiers, les données physiques PostgreSQL et les logs locaux sont ignorés par Git.
Un nouveau lancement réimporte les données sans dupliquer les lignes ni effacer les traces.

```bash
uv run --no-sync python scripts/local_postgres.py status
uv run --no-sync python scripts/local_postgres.py stop
```

Pour recréer entièrement `hrnova`, le script sauvegarde d'abord la base au format
`pg_dump` dans `.local/backups`, puis supprime uniquement `hrnova`, la recrée et réimporte
le dataset. L'historique actif repart de zéro ; il reste dans la sauvegarde locale :

```bash
uv run --no-sync python scripts/local_postgres.py recreate
```

Sur une autre installation, renseigner `--pg-bin /chemin/vers/postgresql/bin`.
Pour un serveur déjà démarré, copier `.env.example` vers `.env`, renseigner `DATABASE_URL`
avec un rôle de création/import, puis exécuter :

```bash
uv run --no-sync python create_db.py --create-database
```

`DATABASE_ADMIN_URL` peut désigner une connexion à la base `postgres` avec le droit
`CREATEDB`. Les tables et l'import utilisent `DATABASE_URL`, qui doit alors disposer
des droits de création de tables et d'écriture. Sans `--create-database`, la base doit
déjà exister. Après l'import, configurer l'API avec un rôle applicatif limité.
Le script local réalise automatiquement cette séparation.

`create_db.py` valide l'unicité des identifiants, leur concordance entre les sources
et la couverture des variables préparées. L'import des trois CSV et des variables est
une transaction : une erreur annule les modifications de données. Une réimportation
met à jour les lignes existantes ; elle ne supprime pas l'historique. Le script est
prévu pour une initialisation/réimportation séquentielle, sans exécutions concurrentes.
`create_all` crée les tables absentes ; les évolutions d'un schéma déjà installé
nécessiteront des migrations explicites.

Les variables préparées proviennent de l'artefact local exporté par le notebook ;
son SHA-256 identifie la version exacte utilisée. L'artefact n'est jamais accepté
depuis un upload API. Après un nouvel export, réimporter avec le rôle administrateur
(`scripts/local_postgres.py start`), puis redémarrer l'API pour renouveler son cache modèle.
L'entraînement et l'analyse exploratoire restent réalisés dans le notebook ; la
traçabilité systématique décrite ici concerne toutes les interactions d'inférence de l'API.

## Circuit obligatoire des prédictions

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant D as PostgreSQL
    participant M as Modèle
    C->>A: JSON, CSV ou identifiant salarié
    A->>D: INSERT api_exchanges (pending), COMMIT
    A->>A: Validation des variables et des labels
    A->>D: INSERT model_inputs, COMMIT
    A->>D: SELECT model_inputs ORDER BY row_index
    D-->>A: Variables et labels persistés
    A->>M: predict / predict_proba / score
    M-->>A: Résultats
    A->>D: INSERT model_outputs, COMMIT
    A->>D: SELECT model_outputs
    D-->>A: Résultat persisté
    A->>D: UPDATE api_exchanges (statut, code HTTP, fin), COMMIT
    A-->>C: Résultat et en-tête X-Request-ID
```

Tous les appels au modèle sont centralisés dans [`inference.py`](../inference.py).
Les routes JSON, CSV et salarié par ID utilisent ce circuit. La route par ID lit les
variables dans `prepared_employees`, sans utiliser le dictionnaire embarqué dans le modèle.
`model_outputs.payload` conserve le résultat métier renvoyé ; `model_values` conserve
les sorties directes du modèle, notamment les probabilités de toutes les classes.
Pour un score, les vraies réponses figurent dans `model_inputs.target`.

Chaque requête HTTP reçoit un identifiant généré côté serveur (`X-Request-ID`).
Le journal inclut aussi les rejets de validation (422), les salariés inconnus (404),
les erreurs et les consultations `/health`, `/features` et `/docs`.
Les fichiers invalides ne déclenchent aucun appel modèle et leur contenu brut n'est
pas enregistré ; le journal conserve la route, les dates et le code d'erreur.
Les paramètres acceptés sont normalisés avant leur enregistrement comme inputs.

Si la BDD est indisponible, l'API renvoie 503 et ne commence aucun calcul.
Si le modèle échoue, les inputs restent enregistrés et la requête est marquée `failed`.
Une sortie non persistée n'est jamais renvoyée au client. En cas d'arrêt brutal ou
de perte de connexion pendant la finalisation, une requête peut rester `pending` :
ce statut permet d'identifier les opérations incomplètes. Aucun mécanisme de reprise
automatique ne réexécute une requête.

## Exemples d'utilisation et de consultation

Pour les messages détaillés, les durées et les erreurs, consulter le
[guide des logs API et de la vue DBeaver `api_logs`](api_logs.md).

```bash
uv run --no-sync uvicorn api:app --reload
curl -i http://127.0.0.1:8000/employees/1/score
curl -i -X POST http://127.0.0.1:8000/predict/file -F 'file=@employes_prepares.csv'
curl -i -X POST http://127.0.0.1:8000/predict-proba/file -F 'file=@employes_prepares.csv'
curl -i -X POST http://127.0.0.1:8000/score/file -F 'file=@employes_prepares_avec_cible.csv'
```

Connexion depuis pgAdmin ou `psql` : hôte `127.0.0.1`, port `5433`, base `hrnova`,
utilisateur `hrnova_app`, mot de passe disponible dans `.env`.

```sql
-- Dataset complet et jointure des trois sources.
SELECT COUNT(*) FROM employees e
JOIN surveys s ON s.employee_id = e.id_employee
JOIN evaluations v ON v.employee_id = e.id_employee;

-- Historique des échanges.
SELECT id, endpoint, operation, status, http_status, started_at, completed_at
FROM api_exchanges ORDER BY started_at DESC LIMIT 20;

-- Entrées et sorties d'une requête (remplacer l'UUID de X-Request-ID).
SELECT i.row_index, i.employee_id, i.features, i.target, o.payload, o.model_values
FROM model_inputs i JOIN model_outputs o ON o.exchange_id = i.exchange_id
WHERE i.exchange_id = 'UUID_DE_LA_REQUETE' ORDER BY i.row_index;

-- Échecs et opérations interrompues.
SELECT id, endpoint, status, error_type FROM api_exchanges
WHERE status IN ('pending', 'failed');
```

## Accès et validation

Le serveur dédié écoute uniquement sur l'interface locale et utilise SCRAM-SHA-256.
Le rôle `hrnova_app` n'est ni superutilisateur, ni créateur de bases ou de rôles.
Il peut lire les tables, insérer les échanges/inputs/outputs et finaliser les échanges.
Il ne peut pas modifier le dataset, mettre à jour les sorties ou supprimer l'historique.
Le rôle administrateur sert uniquement au provisionnement et à l'import.
L'API est destinée à un usage local ; une exposition réseau nécessiterait une
authentification et des autorisations HTTP adaptées aux données RH.

Les tests couvrent le commit des inputs avant calcul, leur relecture depuis une autre
session, la concordance de la réponse et de la sortie stockée, les échecs du modèle,
les erreurs d'écriture et l'absence de BDD. L'import complet est testé deux fois pour
vérifier son idempotence. GitHub Actions démarre PostgreSQL 18 et utilise un schéma
isolé par test ; les mêmes tests peuvent utiliser SQLite pour une exécution unitaire rapide.

Le [rapport de validation locale](database_validation.json) contient les comptages et
les identifiants des échanges réellement vérifiés avec le rôle applicatif.
Pour régénérer ce rapport et contrôler la conservation exacte de toutes les valeurs
source (cette commande crée cinq échanges tracés dans la base) :

```bash
uv run --no-sync python scripts/verify_database.py
```

```bash
uv run --no-sync pytest
# Avec une BDD PostgreSQL dédiée aux tests et un rôle autorisé à créer des schémas :
TEST_DATABASE_URL='postgresql+psycopg://utilisateur:mot_de_passe@127.0.0.1:5433/base_test' \
  uv run --no-sync pytest
```

Références : [transactions SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html),
[création d'une base PostgreSQL](https://www.postgresql.org/docs/18/sql-createdatabase.html)
et [privilèges PostgreSQL](https://www.postgresql.org/docs/18/ddl-priv.html).
