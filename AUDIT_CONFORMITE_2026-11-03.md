# Audit de conformité HRNova — 3 novembre 2026

> **État historique avant corrections.** Les six points demandés ont ensuite été traités ; consulter [la recette et les preuves actualisées](docs/validation.md). Les constats ci-dessous décrivent l’état audité initialement.

Révision examinée : `c9edeb2` (`ajout authentification`), avec l’état du répertoire de travail présent pendant l’audit. Référentiel : critères transmis dans la conversation, incluant l’acceptation d’un déploiement entièrement local depuis septembre 2026. La fiche Google liée n’était pas accessible à l’outil de lecture ; son contenu distinct n’a pas été audité.

**Avis : le projet couvre une grande partie des compétences, mais la conformité complète n’est pas démontrée.** Le code API, les contrats, la traçabilité, les imports et les tests sont solides. Deux régressions concrètes, la configuration locale incomplète et des manques documentaires doivent être traités avant une démonstration finale. Cet audit ne remplace pas la décision du jury.

L’audit n’a pas modifié le code fonctionnel, créé de compte persistant, démarré de service ni publié de modèle. Les vérifications ont utilisé des bases SQLite isolées et des fichiers temporaires. La construction du package peut actualiser les métadonnées générées `*.egg-info`.

## Sens des statuts

- **Respecté** : preuve dans le livrable, avec vérification exécutée lorsque possible.
- **Partiel** : livrable présent, mais fonctionnement, documentation ou preuve incomplets.
- **Non respecté** : contradiction ou défaut concret observé dans le périmètre décrit.
- **Non vérifié** : vérification impossible dans cet audit ; ce statut ne signifie pas que le travail est absent.

## Vérifications exécutées

| Vérification | Résultat et portée |
| --- | --- |
| Tests Pytest | **200 réussis, 2 ignorés**. Sans `TEST_DATABASE_URL`, la fixture fournit SQLite ; les cas spécifiques PostgreSQL sont ignorés. |
| Couverture du périmètre déclaré par le projet | **100 % des lignes** sur `api`, `schemas`, `audit`, `database`, `inference`, `create_db`. Ce n’est pas 100 % de tout le dépôt. |
| Couverture élargie de l’audit | **840/878 lignes, 95,67 %**, sur les 12 fichiers effectivement importés et mesurés. `auth.py` : 100 % ; `model_release.py` : 88 % ; `scripts/deploy_api.py` : 82 % ; `scripts/manage_users.py` : 91 % ; `scripts/publish_huggingface.py` : 38 %. |
| Scripts non exécutés par Pytest | Coverage signale que `scripts.verify_database` et `scripts.local_postgres` ne sont jamais importés dans cette suite. Ils ne sont donc pas inclus dans le total de 95,67 %. |
| Documentation MkDocs | `mkdocs build --strict` réussit vers un dossier temporaire. Cette réussite garantit la structure et les liens contrôlés, pas l’exactitude fonctionnelle des commandes. |
| Contrat OpenAPI | Le JSON de `docs/openapi.json` correspond exactement à `app.openapi()`. |
| Verrou des dépendances | `uv lock --check --offline` réussit : 232 packages résolus. |
| Construction Python | `uv build` réussit : archive source et wheel produits en dossier temporaire. Le premier essai hors ligne était limité par l’absence des outils de build en cache ; l’essai avec téléchargement autorisé réussit. |
| PostgreSQL existant | `pg_ctl -D .local/postgres status` retourne **no server running**. Connexion impossible, y compris hors sandbox. Aucun service n’a été démarré pour cet audit. |
| API locale sur le port 8000 | Aucun processus en écoute détecté par `lsof`. Cela ne teste pas d’autres machines ou ports. |
| Comptes HTTP locaux | `HRNOVA_AUTH_USERS` absent/vide dans l’environnement effectif chargé par `.env` : aucun accès protégé opérationnel dans cette configuration. Aucun secret n’a été imprimé. |
| Script de validation BDD | Échec **reproduit** avec modèle réel, dataset importé dans une base SQLite isolée et compte admin temporaire configuré : premier appel `/predict/file` rejeté en **401**, car le client n’envoie pas d’identifiants. |
| Build Docker | Docker indisponible sur cette machine ; construction non exécutée. Défaut bloquant établi statiquement : `.dockerignore` exclut deux sources explicitement demandées par `COPY`. |

Les rapports courants se trouvent dans `reports/audit_2026-11-03/` : `junit.xml`, `coverage_elargie.json`, `etat_local.json`. Ce répertoire est ignoré par Git ; joindre ces pièces séparément si nécessaire.

## Matrice des compétences

### 1. Configurer l’environnement de travail

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| Dépôt Git et suivi des versions | Respecté | Historique Git disponible ; 11 commits examinés ; code, schémas, données et workflow versionnés. |
| CE1 — Dépendances nécessaires dans requirements ou équivalent | Respecté pour les parcours documentés | `pyproject.toml` et `uv.lock`, extras `api`, `dev`, `docs`, `publish`. Le parcours publication exige les extras `publish` et `api`, comme dans la CI actuelle. Un fichier nommé exactement `requirements.txt` n’est pas obligatoire. |
| CE2 — Configuration cohérente des services | Partiel | PostgreSQL, ports, API et variables sont définis ; la chaîne Docker comporte cependant un défaut de contexte de construction. |
| CE2 — Configuration documentée | Partiel | Guides d’installation, BDD, environnements et authentification présents ; certaines commandes et affirmations sont périmées depuis l’ajout des rôles. |
| CE3 — Environnement testé et fonctionnel | Partiel | Tests et build Python réussissent ; service PostgreSQL arrêté, API non démarrée et comptes HTTP non configurés au moment de l’audit. Le fonctionnement du service réellement déployé n’est pas confirmé aujourd’hui. |
| CE3 — Installation automatisée lors du déploiement | Non respecté pour la chaîne Docker actuelle | Dockerfile et `uv sync --locked` présents, mais `.dockerignore` empêche de fournir `auth.py` et `model_release.py` à `COPY`. L’installation locale par uv reste possible. |
| Conventions de nommage et commits documentés | Partiel | Code globalement organisé, mais messages tels que `/fix bug`, `ajout bdd`, `ajout hugging face` trop vagues pour retracer les décisions. Aucun corps explicatif dans les cinq derniers commits examinés. Des `.pyc` et fichiers `*.egg-info` sont déjà suivis malgré `.gitignore`. |
| Pydantic intégré dès la première API | Respecté pour la présence | Le commit initial d’API `3e1cd40` importe déjà Pydantic et définit les modèles de requête/réponse. Les validations strictes ont été renforcées ensuite. Le fait d’avoir compris l’architecture avant de coder ne peut pas être prouvé par le seul état du dépôt. |

### 2. Infrastructure, CI/CD et API

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| CE1 — Développement, test, production | Respecté dans la configuration | Workflow avec tests PostgreSQL isolés et ciblage `development`, `staging`, `production` ; exemples `.env` séparés et ports documentés. Le test est un job/service isolé, sans nécessité d’un environnement GitHub nommé littéralement `test`. |
| CE1 — Gestion des secrets | Respecté dans le code, activation non vérifiée | Références `secrets.*`, `.env`/`.local` ignorés, mots de passe non imprimés. Aucun fichier `.env`, `.local` ou `.aws` trouvé dans les chemins suivis contrôlés. Audit exhaustif de tous les secrets de l’historique non réalisé. |
| CE2 — YAML de tests et de déploiement | Respecté pour la présence ; exécution partielle | `.github/workflows/ci.yml` automatise tests, build, documentation, publication et prévoit le déploiement API. Ce dernier est conditionné par `ENABLE_API_DEPLOYMENT=true`, des runners et des secrets. Leur configuration réelle sur GitHub n’est pas vérifiée. Le défaut Docker bloque la branche de déploiement si activée. |
| CE3 — FastAPI exposant le modèle | Respecté au niveau applicatif | `api.py`, `inference.py`, modèle joblib, endpoints JSON/CSV/ID salarié ; comportement couvert par tests. |
| CE3 — API déployée localement et fonctionnelle | Partiel / non démontré actuellement | Aucun serveur détecté sur le port 8000 ; PostgreSQL arrêté et comptes HTTP absents. Présenter une requête réelle sur un service lancé reste nécessaire. Les tests TestClient ne prouvent pas à eux seuls qu’un service est déployé. |
| CE3 — Swagger/OpenAPI, schémas et exemples | Respecté | `/docs`, `/redoc`, `/openapi.json`, modèles Pydantic, exemples JSON/CSV dans `examples/` et guides d’appels. Export OpenAPI à jour. |
| CE3 — Validation sans erreurs pour des données conformes | Respecté dans les tests | Champs obligatoires, types, nombres finis, colonnes exactes, tailles CSV, classes et probabilités vérifiés. Un rejet volontaire 422 d’une entrée incorrecte est attendu et ne constitue pas une non-conformité. |
| Instructions claires d’installation/configuration/utilisation | Partiel | Documentation riche mais authentification non répercutée dans tous les exemples et script de validation annoncé fonctionnel alors qu’il échoue. |
| Justification des choix et cible finale | Respecté | `docs/architecture.md`, `docs/deployment.md` et `docs/model.md` expliquent FastAPI, PostgreSQL, SQLAlchemy, JSONB, uv, traçabilité, entraînement hors ligne et compromis. Cible locale et hébergement futur décrits. |
| API performante et capacité de volume | Partiel | Modèle en cache, index, pool SQLAlchemy et limite CSV 10 Mio. Aucun benchmark de charge ni objectif de latence/débit fourni ; le volume démontré concerne 1 470 salariés. Cela ne justifie pas d’inventer une obligation de production à grande échelle, mais les performances annoncées restent à mesurer. |

Le déploiement cloud et un Space Hugging Face ne sont pas requis selon le référentiel transmis. Publier un fichier sur le Model Hub est distinct de déployer FastAPI et ne remplace pas la démonstration locale.

### 3. Architecture des données et BDD

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| CE1 — Modèle détaillé et compréhensible | Respecté | `database.py`, `docs/schema.sql`, diagramme Mermaid de `docs/database.md` ; 8 tables et vue `api_logs`. |
| CE2 — BDD fonctionnelle | Partiel pour la preuve actuelle | ORM et transactions testés. Instance locale existante mais arrêtée ; contenu réel PostgreSQL non relu aujourd’hui. Le rapport historique est daté du 20 octobre 2026. |
| CE3 — Création par SQL/Python | Respecté pour le livrable et les tests | `create_db.py`, `scripts/local_postgres.py` et migration SQL additive. Tests de création, idempotence et rollback. |
| CE3 — Dataset inséré | Respecté dans les imports testés, non revalidé sur PostgreSQL actuel | Import réel des 3 CSV dans les tests ; 1 470 lignes/source, correspondance des ID et valeurs, conservation des codes à zéros initiaux. `docs/database_validation.json` atteste une exécution historique, pas la version actuelle après authentification. |
| CE4 — Exemples d’entrées et sorties | Respecté pour les livrables | CSV/JSON synthétiques, tests et rapport historique comportant les IDs de requêtes et les comptages. |
| CE4 — Journal des interactions utilisateur/modèle | Respecté dans les API testées | `audit.py` et `inference.py` : `X-Request-ID`, inputs écrits/relus avant calcul, outputs validés/écrits/relus avant réponse, échecs tracés ; compte et rôle dans les échanges authentifiés. Les inférences Python directes hors API ne sont pas tracées par ce mécanisme. |
| CE4 — Relations et contraintes | Respecté pour le socle ; renforcement possible | PK, FK, NOT NULL, UNIQUE et CHECK de statut ; JSONB versionné. Les bornes de classe/cible/seuil sont davantage imposées dans l’application que par des CHECK SQL. Les contraintes PostgreSQL spécifiques doivent être revérifiées avec les tests d’intégration. |
| CE4 — Efficacité sur le volume traité | Partiel | Import complet et index présents ; pas de mesure de charge/concurrence, de volumétrie de croissance ou de politique de conservation des traces. |

### 4. Installation et paramétrage du SGBD et extraction

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| CE1 — Script d’initialisation correcte | Respecté pour le code ; exécution PostgreSQL actuelle non vérifiée | Création de base et schéma, import transactionnel, migrations, droits séparés. Les binaires PostgreSQL système doivent déjà être installés ; ce prérequis est documenté. |
| CE2 — Paramétrage du SGBD et extraction | Respecté dans la configuration | `.local/postgres/pg_hba.conf` utilise SCRAM-SHA-256 ; `postgresql.conf` restreint l’écoute à 127.0.0.1:5433 ; Pandas extrait les CSV, SQLAlchemy intègre les données. Les privilèges effectifs n’ont pas pu être relus, serveur arrêté. |
| CE3 — Tables et relations créées | Respecté dans les tests ; preuve PostgreSQL courante à refaire | Création ORM et import testés en base isolée ; migration/vue PostgreSQL et création d’une base temporaire font partie des 2 tests ignorés sans `TEST_DATABASE_URL`. |

### 5. Authentification et sécurité des données

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| CE1 — Méthodes et accès documentés dans le README BDD | Respecté par documentation liée | Le README principal renvoie au guide BDD ; `docs/database.md` documente SCRAM et les privilèges, et lie `docs/authentication.md` pour HTTP Basic et rôles. Le nom de fichier exact « README BDD » n’est pas nécessaire si le contenu est clairement accessible. |
| CE2 — Système d’authentification opérationnel | Partiel | Code fonctionnel et tests réels 401/403, comptes désactivés, séparation `utilisateur` / `livreur` / `admin`. Aucun compte configuré dans l’environnement local effectif ; le service n’est pas prêt à l’emploi tant que l’opérateur ne les a pas créés. |
| CE3 — Secrets et mots de passe | Respecté au niveau applicatif contrôlé | PBKDF2-SHA256, sel aléatoire, 600 000 itérations, comparaison constante, fichiers de comptes en mode 600, absence d’en-tête Authorization dans les journaux, token HF injecté par secrets. SCRAM côté PostgreSQL. |
| CE3 — Bonnes pratiques selon l’exposition | Partiel | Usage local lié à loopback cohérent ; HTTPS explicitement requis hors machine locale. Ni proxy HTTPS ni limitation des tentatives livrés. Ne pas qualifier l’absence de TLS local d’échec automatique au référentiel ; pour une exposition distante, ces protections doivent être mises en place. |
| CE3 — Respect de la législation | Non validé juridiquement / documentation partielle | Pas de politique explicite de durée de conservation/purge, de finalités, d’accès analytiques ou de statut des données RH d’étude identifiée dans les guides. Ces éléments sont à clarifier ; ce constat ne prouve pas une infraction et cet audit technique ne certifie pas la conformité légale. Le modèle exporté exclut les lignes sources, ce qui n’est pas une preuve d’anonymisation. |

### 6. Processus de tests SGBD et application

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| CE1 — Intégrité des données testée | Respecté dans le périmètre exécuté | Types, absence/présence, finitude, catégories cibles, doublons, correspondance CSV, idempotence et rollback testés. Sans serveur PostgreSQL, les FK et comportements propres à PostgreSQL ne sont pas tous validés par SQLite. |
| CE2 — Insertion, lecture, modification et erreurs | Respecté dans la suite isolée ; intégration PG à confirmer | Commits/relectures, import transactionnel, sortie identique à la réponse, échecs d’inputs/outputs, absence de BDD et modèle défaillant couverts. La suppression par le rôle applicatif est volontairement interdite ; ce n’est pas un manque de fonctionnalité. |
| CE2 — Cas critiques et scénarios d’erreur | Partiel | 200 tests réussis, mais pas de test exécutant `verify_database.main()` avec l’authentification, ni de contrôle attrapant l’incohérence Dockerfile/.dockerignore. La régression 401 est reproductible malgré tous les tests verts. |
| CE3 — Rapport de couverture | Respecté pour la présence ; périmètre à expliciter | Configuration et rapports XML/HTML/CI présents. Le seuil de 100 % du workflow exclut `auth.py`, `model_release.py` et les scripts ; la mesure élargie d’audit est de 95,67 % sur ses fichiers mesurés, avec des scripts encore hors mesure. La couverture seule ne prouve pas la robustesse d’un déploiement. |
| Script Python de vérification globale | Non respecté dans sa version actuelle | `scripts/verify_database.py:70-82` crée un TestClient puis appelle toutes les routes sans `auth` : premier appel rejeté en 401 même avec un compte admin configuré. |

### 7. Documentation et processus de stockage

| Critère | Statut | Preuve et observation |
| --- | --- | --- |
| README principal | Respecté pour la présence et l’organisation | Parcours d’installation, usage, documentation liée, modèle, tests et déploiement. |
| Swagger/OpenAPI | Respecté | Contrat généré à jour, schémas et routes sécurisées exposées dans la documentation. |
| MkDocs | Respecté | Navigation, Mermaid, recherche ; build strict exécuté avec succès. |
| CE1 et CE3 — Processus de stockage détaillé et clair | Respecté sur le circuit central | `docs/database.md`, `docs/api_logs.md`, `docs/architecture.md` : extraction, normalisation, stockage source/préparé, transactions, journal, réimport, sauvegarde et restauration. Ajouter une politique de conservation clarifierait le cycle de vie complet. |
| CE2 — Besoins analytiques / tableau de bord décrits | Partiel, formalisation manquante | Des requêtes de consultation et un suivi mensuel sont décrits. Absence de section métier définissant objectifs du tableau de bord, utilisateurs habilités, agrégations/KPI, fréquence, sources, filtres, qualité et modalités d’accès. Un dashboard développé n’est pas exigé par le texte : il faut décrire les besoins. |
| Cohérence documentaire après ajout des rôles | Non respecté sur plusieurs exemples | `docs/installation.md:64-67` dit que le script de publication ne charge pas `.env`, alors qu’il appelle `load_dotenv()` ; `docs/installation.md:85` et d’autres commandes d’accès métier omettent les identifiants. La page d’accueil annonce encore 7 endpoints, alors que le contrat en comporte 9. |

## Défauts concrets et priorités

### P1 — À traiter avant la démonstration

1. **Contexte Docker incomplet.** `.dockerignore:1` exclut tout et ne réautorise ni `auth.py` ni `model_release.py`, pourtant requis par `Dockerfile:10`. Ajouter les deux exceptions puis exécuter un vrai `docker build`. Le défaut est établi par inspection ; la sortie d’un build Docker n’a pas été collectée car Docker n’est pas installé ici.
2. **Validation BDD cassée.** Adapter `scripts/verify_database.py` pour recevoir un compte autorisé via des secrets et authentifier ses appels, sans désactiver la sécurité. Ajouter un test de ce parcours. L’échec 401 a été reproduit en environnement isolé.
3. **Préparer le service local.** Démarrer PostgreSQL et FastAPI ; créer au moins les comptes `utilisateur` et `livreur` ; vérifier `/auth/me`, une inférence tracée et le téléchargement selon le rôle. L’absence de service aujourd’hui n’établit pas que le code ne peut pas fonctionner, mais ne permet pas de valider le critère « API déployée fonctionnelle ».
4. **Revalider réellement PostgreSQL.** Exécuter la suite avec `TEST_DATABASE_URL` sur une base dédiée puis régénérer `docs/database_validation.json` après correction de l’authentification. Ne pas présenter le rapport du 20 octobre comme preuve de la version du 3 novembre.

Les points 1 et 2 sont des régressions des ajouts précédents d’authentification réalisés dans cette session.

### P2 — À compléter dans les livrables

5. Corriger les exemples et affirmations documentaires touchés par la connexion ; regrouper les secrets nécessaires au déploiement et à la publication.
6. Ajouter une section « besoins analytiques » au guide BDD : objectifs RH et exploitation, rôles lecteurs, KPI et agrégations, sources, actualisation et règles d’accès. Décrire les exigences sans imposer un développement de dashboard non demandé.
7. Expliciter la conservation des inputs/outputs et des traces, leur statut de données d’étude, les accès et le processus de purge/archivage si applicable.
8. Étendre et expliciter le périmètre de couverture ; couvrir les parcours de scripts et la cohérence de construction Docker, pas seulement les lignes déjà suivies.
9. Améliorer les prochains messages de commit et retirer du suivi Git les artefacts générés déjà versionnés ; l’ajout d’une règle `.gitignore` ne les retire pas rétroactivement.

### P3 — Éléments de preuve à apporter

10. Montrer une exécution récente de GitHub Actions réussie, les environnements/secrets définis sans révéler leurs valeurs, et l’activation effective du déploiement si celui-ci est revendiqué. Leur absence n’a pas été constatée ; ils n’ont pas été accessibles pendant cet audit.
11. Si la performance est revendiquée, fournir une petite mesure reproductible : type de requête, nombre de lignes, concurrence, machine, latence et taux d’erreur. Ne pas confondre performance prédictive et temps de réponse API.

## Avis pour la soutenance

Le socle FastAPI/Pydantic/PostgreSQL/SQLAlchemy, le schéma relationnel, la traçabilité et les tests sont présents. La cible locale est acceptable au vu du référentiel transmis. Une affirmation « tout est respecté » serait prématurée tant que les deux régressions et la démonstration courante PostgreSQL/API ne sont pas traitées. Les besoins analytiques et la cohérence documentaire sont les compléments les plus directement liés aux critères restant à formaliser.
