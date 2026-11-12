# HRNova — Guide du livrable MkDocs

Ce livrable contient la documentation consultable dans un navigateur et le PowerPoint de soutenance.

| Vous souhaitez… | Suivre… |
| --- | --- |
| Lire la documentation et consulter la présentation | Étape 1 uniquement |
| Tester les prédictions avec l’API | Étape 2, puis étape 3 |
| Modifier la documentation | Section « Modifier le site » |

## 1. Ouvrir la documentation et la présentation

**Prérequis : Python 3. Aucun compte n’est demandé pour lire la documentation.**
Le dossier peut être copié seul sur une autre machine : le site est déjà construit. PostgreSQL et l’API ne sont pas nécessaires pour le consulter.

Ouvrir un terminal dans le dossier `livrable_mkdocs`, puis exécuter :

```bash
sh lancer.sh
```

Ouvrir **http://127.0.0.1:8002** dans le navigateur. L’onglet **Présentation** permet de télécharger le PowerPoint.

Garder le terminal ouvert pendant la consultation. Pour arrêter le serveur, appuyer sur **Ctrl+C**.

Alternative, depuis ce même dossier :

```bash
# macOS / Linux
python3 -m http.server 8002 --bind 127.0.0.1 --directory site

# Windows
py -m http.server 8002 --bind 127.0.0.1 --directory site
```

Le PowerPoint peut aussi être ouvert directement :
[HRNova — Présentation de soutenance](docs/presentation/HRNova_Soutenance_Infographie_2026-11-10.pptx).

## 2. Installer et lancer l’application complète

Le dossier livré contient le site et la présentation. Pour exécuter l’API et le modèle, télécharger le projet complet depuis GitHub.

**Prérequis :** Git, [uv](https://docs.astral.sh/uv/getting-started/installation/), Python 3.13 et PostgreSQL 18. Une connexion Internet est nécessaire pour télécharger le projet et les dépendances.

Dans un nouveau terminal, depuis le dossier où installer le projet :

```bash
git clone https://github.com/samuelGabbai/P5_Futurisys.git
cd P5_Futurisys
uv sync --locked --python 3.13 --extra api --extra dev --extra docs
```

Si le dépôt est déjà présent, se placer simplement à sa racine, dans `P5_Futurisys`.

Démarrer et initialiser la base locale :

```bash
uv run --no-sync python scripts/local_postgres.py start
uv run --no-sync python scripts/manage_users.py --bootstrap-local
```

Sur le Mac de développement, PostgreSQL est installé dans `/Library/PostgreSQL/18/bin`. Pour une autre installation, adapter la commande :

```bash
uv run --no-sync python scripts/local_postgres.py start --pg-bin /chemin/vers/postgresql/bin
```

La base locale s’appelle `hrnova` et utilise `127.0.0.1:5433`.

### Configurer le compte de démonstration admin / admin

Les identifiants de la démonstration sont :

| Champ | Valeur |
| --- | --- |
| Nom d’utilisateur | `admin` |
| Mot de passe | `admin` |

Sur la machine de démonstration actuelle, ce compte est déjà configuré. Après un nouveau clonage, le bootstrap génère des mots de passe aléatoires : exécuter le bloc suivant **à la racine du projet, avant de lancer l’API**, pour configurer les mêmes identifiants.

```bash
uv run --no-sync python - <<'PY'
import json
from pathlib import Path
from dotenv import dotenv_values, set_key
from auth import hash_password

accounts = json.loads(dotenv_values('.env').get('HRNOVA_AUTH_USERS') or '{}')
accounts['admin'] = {
    'password_hash': hash_password('admin'),
    'role': 'admin',
    'enabled': True,
}
set_key('.env', 'HRNOVA_AUTH_USERS', json.dumps(accounts))
credentials = Path('.local/api-credentials.env')
if credentials.exists():
    set_key(str(credentials), 'HRNOVA_ADMIN_USERNAME', 'admin')
    set_key(str(credentials), 'HRNOVA_ADMIN_PASSWORD', 'admin')
print('Compte de démonstration configuré : admin / admin')
PY
```

Ce bloc s’utilise dans un terminal macOS/Linux ou Bash. Le mot de passe court `admin` est destiné à la démonstration locale. Pour un autre environnement, choisir un mot de passe personnel avec `uv run --no-sync python scripts/manage_users.py admin --role admin` (12 caractères minimum).

Lancer ensuite l’API et garder ce terminal ouvert :

```bash
uv run --no-sync uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

## 3. Se connecter et tester l’API

1. Ouvrir **http://127.0.0.1:8000/docs**.
2. Cliquer sur **Authorize**.
3. Saisir **Username : `admin`** et **Password : `admin`**.
4. Valider avec **Authorize**, puis fermer la fenêtre avec **Close**.
5. Ouvrir `GET /auth/me`, cliquer sur **Try it out**, puis **Execute**.

Une réponse **200** avec `"username": "admin"` et `"role": "admin"` confirme la connexion. Les autres endpoints permettent ensuite de tester les prédictions ; les exemples de requêtes se trouvent dans l’onglet **Référence API** de la documentation.

Depuis un deuxième terminal, la connexion peut aussi être vérifiée avec :

```bash
curl -u admin:admin http://127.0.0.1:8000/auth/me
```

### Si la connexion échoue

- **Erreur 401 :** vérifier les identifiants `admin` / `admin`. Dans Swagger, cliquer sur **Authorize**, puis **Logout**, et se reconnecter.
- **Mot de passe modifié récemment :** arrêter complètement l’API avec **Ctrl+C**, puis relancer la commande `uvicorn`. Le rechargement automatique ne suffit pas pour recharger le fichier `.env`.
- **Erreur 503 :** consulter le message retourné et les logs du terminal de l’API. Vérifier la configuration des comptes, la disponibilité de PostgreSQL et du modèle selon le message.
- **Page inaccessible :** vérifier que le serveur correspondant tourne et que l’adresse utilise le bon port.
- **Port déjà utilisé pour la documentation :** remplacer `8002` par un port libre dans la commande `http.server` et dans l’adresse du navigateur.

## Repères utiles

| Service | Adresse | Terminal à garder ouvert |
| --- | --- | --- |
| Documentation livrée et présentation | http://127.0.0.1:8002 | `sh lancer.sh`, depuis `livrable_mkdocs` |
| API — interface Swagger | http://127.0.0.1:8000/docs | Commande `uvicorn`, depuis la racine du projet |
| API — vérification de l’identité | http://127.0.0.1:8000/auth/me | Même serveur API ; authentification nécessaire |

Après un redémarrage de la machine, relancer PostgreSQL avec `local_postgres.py start`, puis l’API. Il n’est pas nécessaire de réinstaller les dépendances ni de recréer les comptes à chaque lancement.

## Modifier le site

Le dossier contient :

- `site/` : site HTML déjà construit, utilisé par `lancer.sh` ;
- `docs/` : sources de la documentation et fichier PowerPoint ;
- `mkdocs.yml` : configuration de MkDocs.

Après avoir modifié les fichiers de `livrable_mkdocs/docs/`, reconstruire le site depuis la **racine du projet `P5_Futurisys`** :

```bash
uv sync --locked --extra api --extra dev --extra docs
uv run --no-sync mkdocs build --strict -f livrable_mkdocs/mkdocs.yml
```

Le résultat est placé dans `livrable_mkdocs/site/`. Actualiser le navigateur si le serveur du livrable tourne déjà.

Pour travailler avec rechargement automatique :

```bash
uv run --no-sync mkdocs serve -f livrable_mkdocs/mkdocs.yml
```

Utiliser alors l’adresse indiquée dans le terminal.

Code source et guides complets : [dépôt GitHub HRNova](https://github.com/samuelGabbai/P5_Futurisys).
