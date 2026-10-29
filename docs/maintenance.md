# Maintenance, mises à jour et diagnostic

## Protocole régulier

Cette cadence est un protocole à appliquer ; il n'existe pas de tâche planifiée
automatique de réentraînement ou de surveillance dans le dépôt.

| Fréquence | Vérifications | Responsable attendu |
| --- | --- | --- |
| À chaque push/PR | Tests, validation Pydantic, import et traçabilité, documentation et package | CI, avec revue du développeur |
| À chaque journée d'utilisation | Disponibilité `/health`, requêtes `failed` ou `pending`, espace disque et erreurs de connexion | Exploitant local |
| Chaque mois d'utilisation | Durées par route, taux d'erreur, volumes, distribution des scores et variables par rapport à une référence | Développeur et data scientist |
| Chaque trimestre, ou changement métier/données | Performance sur données nouvelles avec vraies réponses, calibration et disparités entre groupes | Data scientist et référent métier |
| Avant chaque mise à jour | Sauvegarde, provenance de l'artefact, compatibilité, métriques documentées et plan de retour arrière | Mainteneur du dépôt |

Définir des critères d'acceptation avec le métier : rappel minimal, précision
acceptable et coût des fausses alertes. Aucune limite de dérive ni alerte statistique
n'est actuellement calculée automatiquement par l'API.

## Mettre à jour le modèle

1. **Sauvegarder** l'artefact complet, les sources et la BDD avant une modification.
   Conserver le commit Git de référence, les versions et les rapports de métriques.
2. **Préparer les données** : vérifier les identifiants et catégories, les valeurs
   manquantes, la cible et les fuites de données. Ajuster les transformations
   apprenantes uniquement sur l'entraînement dans la prochaine pipeline de préparation.
3. **Réentraîner et évaluer** le notebook avec le verrou courant ou une mise à jour
   de dépendances révisée. Garder un test indépendant ; choisir hyperparamètres et
   seuil sans l'utiliser. Comparer au modèle de référence, y compris calibration,
   rappel/précision, temps de calcul et erreurs par sous-population.
4. **Exporter** l'artefact complet via la cellule d'export du notebook, avec les
   variables préparées indexées par salarié. Si le contrat change, adapter schémas,
   exemples et consommateurs dans la même modification.
5. **Documenter** les nouveaux résultats et leurs limites dans `docs/model.md`,
   `docs/model_metrics.json` et `docs/features.md`. Relever les nouveaux SHA-256
   avec `shasum -a 256 artifacts/turnover_model.joblib dataScientistTechNova.ipynb`.
6. **Vérifier** tests, documentation, installation et export sans données salariées.
   Ouvrir une PR pour revue et conserver les rapports avant fusion.
7. **Importer localement** avec le rôle administrateur via `local_postgres.py start`,
   puis **redémarrer l'API** pour renouveler le cache de l'artefact. Vérifier `/health`,
   `/features`, les exemples et `scripts/verify_database.py`.
8. **Publier** après fusion sur `main` : la CI envoie l'export validé vers Hugging Face
   si le secret est configuré. Contrôler le commit et le hash dans `metadata.json`.

```bash
uv sync --locked --extra api --extra dev --extra docs
uv run --no-sync pytest --cov-report=xml --junitxml=reports/junit.xml
uv run --no-sync mkdocs build --strict
uv build
uv run --no-sync python scripts/local_postgres.py start
uv run --no-sync python scripts/verify_database.py
```

Le modèle original garde `records_by_employee_id` pour l'import local ; l'export
Hugging Face ne le contient pas. Les deux fichiers ont donc des hashes différents.
Ne pas écraser l'original avec l'export public.

## Dépendances et évolution du schéma

Modifier les dépendances dans une branche dédiée, exécuter `uv lock` puis les tests
avant de versionner `pyproject.toml` et `uv.lock` ensemble. Scikit-learn est fixé
à `1.7.2` : une mise à jour peut exiger un réentraînement et un nouvel export, les
objets joblib ne garantissant pas une compatibilité entre versions.

Les tables absentes sont créées par SQLAlchemy. Les modifications de tables existantes
doivent être décrites dans une migration explicite et appelées par le script
d'initialisation. La migration de logs `docs/migrations/002_explicit_api_logs.sql`
est additive et réexécutable. Il n'y a pas de gestionnaire Alembic automatique.
Tester toute nouvelle migration sur une copie de la base et vérifier les droits
du rôle applicatif après création de nouvelles tables ou vues.

## Sauvegardes et retour arrière

Le dossier `.local` doit être sauvegardé comme une donnée locale ; il n'est pas dans Git.
Pour une sauvegarde ponctuelle, utiliser le binaire PostgreSQL de l'installation :

```bash
mkdir -p .local/backups
/Library/PostgreSQL/18/bin/pg_dump -h 127.0.0.1 -p 5433 -U hrnova_admin \
  -Fc -f .local/backups/hrnova_avant_mise_a_jour.dump hrnova
```

Le mot de passe administrateur est dans `.local/admin.env` et doit être fourni au
prompt ou via un mécanisme local approprié ; ne pas le committer. Le fichier de
sauvegarde contient des données RH et l'historique d'inférence.
`local_postgres.py recreate` réalise également une sauvegarde datée avant de remplacer
`hrnova`, mais cette commande efface l'historique actif et ne sert pas de maintenance courante.

Pour tester une restauration **dans une autre base** :

```bash
/Library/PostgreSQL/18/bin/createdb -h 127.0.0.1 -p 5433 -U hrnova_admin hrnova_restore
/Library/PostgreSQL/18/bin/pg_restore -h 127.0.0.1 -p 5433 -U hrnova_admin \
  --no-owner --no-privileges -d hrnova_restore .local/backups/hrnova_avant_mise_a_jour.dump
```

Ce test ne remplace pas la base active. Pour un retour arrière du service, rétablir
le commit applicatif et l'artefact complet compatibles, sélectionner/restaurer la
base voulue, réappliquer les droits du rôle applicatif puis redémarrer et tester.
Une ancienne version de modèle reste référencée dans `model_versions` et les traces ;
restaurer le fichier exact permet de retrouver son hash. Vérifier aussi la compatibilité
du code et du schéma avant de remettre une version en service.

Une publication de retour arrière sur Hugging Face se fait depuis un nouveau commit
`main` rétablissant le modèle voulu, afin de conserver un historique clair. Les artefacts
GitHub sont conservés 14 jours ; ils ne remplacent pas un archivage durable des versions.

## Diagnostic des problèmes courants

| Symptôme | Cause possible et action |
| --- | --- |
| Connexion refusée sur `5433` | Lancer `uv run --no-sync python scripts/local_postgres.py status`, puis `start` si arrêté |
| DBeaver indique une erreur pour `postgres` | Le compte applicatif est `hrnova_app`, base `hrnova`, port `5433` ; vérifier le mot de passe dans `.env` |
| API 503 au début de chaque requête | Vérifier `DATABASE_URL`, le serveur et les droits de lecture/écriture des tables de journal ; lire aussi les logs du processus |
| API 503 « modèle non enregistré » | Réimporter l'artefact complet avec `local_postgres.py start`, puis redémarrer l'API |
| Modèle absent ou artefact invalide | Vérifier `HRNOVA_MODEL_PATH`, le fichier de confiance et les versions du verrou |
| CSV refusé en 422 | Lire les variables de `/features`, contrôler encodage, séparateur, valeurs et cible ; voir [validation](api_validation.md) |
| Prédictions JSON et CSV différentes | La route JSON applique le seuil optimisé ; `/predict/file` utilise la décision native |
| Requête 500 pendant le calcul | Rechercher le `X-Request-ID` dans `api_logs` ; contrôler `etape` et `detail_erreur` |
| Trace `pending` persistante | Contrôler les logs du processus et les tables input/output ; un arrêt brutal a pu interrompre la finalisation |
| Publication Hugging Face refusée | Vérifier le secret `HF_TOKEN`, ses droits d'écriture, le dépôt cible et les approbations de l'environnement `production` |
| Documentation impossible à construire | Synchroniser l'extra `docs`, puis corriger les liens ou références signalés par `mkdocs build --strict` |

```sql
SELECT date_requete, requete_id, route, code_http, etape, message, detail_erreur
FROM api_logs
WHERE statut IN ('failed', 'pending')
ORDER BY date_requete DESC;
```

La durée enregistrée exclut l'écriture finale du log et le transfert réseau.
Une réémission de requête crée un nouvel ID et peut recalculer une prédiction ;
ne pas assimiler automatiquement toutes les tentatives au même échange.
