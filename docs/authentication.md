# Authentification et droits d’accès

L’API utilise HTTP Basic : chaque requête protégée envoie le nom et le mot de passe
dans l’en-tête `Authorization`. Utiliser HTTPS hors de la machine locale : l’encodage
Basic ne chiffre pas les identifiants. Il n’y a pas de jeton ni de session persistante.

Deux droits métier sont séparés : **utilisation des API** et **livraison du modèle**.

| Rôle | Utiliser les API métier | Télécharger le modèle | Publier sur Hugging Face |
| --- | --- | --- | --- |
| `utilisateur` | Oui, y compris les scores par identifiant | Non | Non |
| `livreur` | Non | Oui | Oui, avec un token Hugging Face autorisé |
| `admin` | Oui | Oui | Oui, avec un token Hugging Face autorisé |

Les rôles précédents restent compatibles : `lecteur` consulte `/features` ;
`analyste` consulte les variables et lance les prédictions sans accès aux scores par ID.
Ils n’ont pas le droit de livrer le modèle. `/auth/me` est accessible à tout compte actif.

`/health`, `/docs`, `/redoc` et `/openapi.json` restent publics pour la supervision
et la consultation du contrat. Les scores RH par identifiant nécessitent `utilisateur` ou `admin`.

## Créer les comptes

Depuis la racine du projet :

```bash
uv run --no-sync python scripts/manage_users.py admin --role admin
uv run --no-sync python scripts/manage_users.py application --role utilisateur
uv run --no-sync python scripts/manage_users.py livraison --role livreur
```

La commande demande et confirme le mot de passe sans l’afficher. Elle conserve un
hash PBKDF2-SHA256 avec un sel aléatoire et 600 000 itérations dans
`HRNOVA_AUTH_USERS`, dans `.env` (permissions 600). Aucun compte par défaut n’existe.
Le nom et le mot de passe doivent être ASCII pour la compatibilité HTTP Basic.
Redémarrer l’API après chaque changement. Une variable déjà exportée dans le processus
prend priorité sur `.env` : actualiser aussi les secrets du service si nécessaire.

Relancer la commande pour changer le mot de passe ou le rôle. Pour désactiver :

```bash
uv run --no-sync python scripts/manage_users.py application --role utilisateur --disable
```

Une configuration absente ou invalide bloque les accès protégés avec HTTP 503.
Un compte inconnu, désactivé ou un mauvais mot de passe renvoie 401 ; un rôle
insuffisant renvoie 403. La traçabilité existante nécessite également une BDD disponible.

## Se connecter

Dans Swagger (`/docs`), cliquer sur **Authorize**, puis saisir ses identifiants.
Pour vérifier son identité avec curl (le mot de passe est demandé) :

```bash
curl -u admin http://127.0.0.1:8000/auth/me
curl -u admin http://127.0.0.1:8000/employees/1/score
curl -u application -H 'Content-Type: application/json' \
  --data-binary @examples/predict.json http://127.0.0.1:8000/predict
```

Ajouter `-u NOM` aux exemples curl des autres guides. Avec Python/httpx, utiliser
`auth=(nom, mot_de_passe)` en lisant le secret depuis l’environnement ou un gestionnaire
de secrets. Les journaux conservent le nom et le rôle authentifiés, sans l’en-tête Basic.

## Déploiement

Configurer `HRNOVA_AUTH_USERS` dans les secrets de chaque environnement, avec le JSON
généré par la commande (`--env-file` permet de choisir un autre fichier). Ne jamais
committer les fichiers contenant les comptes. Docker Compose exige cette variable.
Pour une valeur dans un fichier Compose `.env`, garder les apostrophes autour du JSON
afin de préserver les caractères `$` des hashes.

Le contrôle de prédiction de `scripts/deploy_api.py` utilise les variables
`HRNOVA_SMOKE_USERNAME` et `HRNOVA_SMOKE_PASSWORD` du processus de déploiement. Le compte
doit avoir le rôle `utilisateur`, `analyste` ou `admin`. Ces deux variables sont transmises seulement
au processus de contrôle via `docker compose exec --env`, sans valeur en argument.
Les variables doivent également être ajoutées aux secrets injectés par la CI.

Cette authentification ne fournit ni limitation des tentatives ni gestion des comptes
en libre-service. Pour un service exposé, configurer la limitation des tentatives au
niveau du proxy HTTPS ; la gestion des comptes reste réservée à l’opérateur.

## Télécharger et publier le modèle

Avec un compte `livreur` ou `admin` :

```bash
curl --fail -u livraison http://127.0.0.1:8000/model/download --output hrnova-model.zip
```

L’archive contient `turnover_model.joblib`, `metadata.json`, `requirements.txt` et
`README.md`. Elle utilise le même export que Hugging Face : les lignes individuelles
et les clés privées de l’artefact source sont exclues. Le SHA-256 source et celui
de l’export sont enregistrés dans les métadonnées. `HRNOVA_MODEL_REVISION` peut
indiquer le commit Git ; sa valeur par défaut est `local`.

La publication par `scripts/publish_huggingface.py` vérifie le même droit
`model:deliver` **avant tout appel à Hugging Face**. Configurer les secrets
`HRNOVA_AUTH_USERS`, `HRNOVA_DELIVERY_USERNAME`, `HRNOVA_DELIVERY_PASSWORD` et
`HF_TOKEN` dans l’environnement GitHub `production` (ou le processus local).
Un compte `utilisateur` reste refusé même si un token Hugging Face est disponible.
Le rôle `livreur` n’accorde pas à lui seul de droits sur le service Hugging Face :
le token doit aussi autoriser l’écriture sur le dépôt cible.

La préparation locale `--prepare-only` ne publie rien et reste accessible sans compte.
Les personnes ayant accès au dépôt source ou aux artefacts CI peuvent déjà obtenir
le modèle par ces canaux : restreindre aussi les accès GitHub et la visibilité du
dépôt Hugging Face si sa distribution doit être privée.
