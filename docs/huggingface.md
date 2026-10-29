# Publication automatique du modèle sur Hugging Face

Le workflow `.github/workflows/ci.yml` prépare un export du modèle après les tests.
Un push sur `main` (ou un lancement manuel sur `main`) publie ensuite cet export
dans un dépôt **Model** Hugging Face, si les tests, la construction et la validation
de l'environnement ont réussi. Les pull requests et les autres branches ne publient pas.

## Configuration à faire une fois

1. Le dépôt **Model** cible est `SamGabb/hrnova` : <https://huggingface.co/SamGabb/hrnova>.
   Vérifier qu'il existe sur Hugging Face.
   Choisir sa visibilité dans Hugging Face. Le workflow utilise un dépôt existant.
2. Créer un token Hugging Face avec permission d'écriture sur ce dépôt, de préférence
   un token à portée fine limité à ce dépôt.
3. Dans le dépôt GitHub, ouvrir **Settings → Secrets and variables → Actions** :
   - onglet **Variables** (facultatif) : ajouter `HF_REPO_ID` pour remplacer `SamGabb/hrnova` ;
   - onglet **Secrets** : ajouter le secret `HF_TOKEN` avec le token.
   Le secret peut aussi être défini dans l'environnement GitHub `production`.
4. Si `production` impose une approbation, approuver les jobs concernés dans GitHub Actions.
5. Pousser sur `main`. Le job **Publier le modèle sur Hugging Face** transmet l'export
   après réussite des vérifications. Un token manquant provoque un échec explicite
   du job de publication, sans envoi de fichiers.

Ne pas ajouter le token au code, à une commande Git ou au fichier YAML.

## Export et traçabilité

Le script [`scripts/publish_huggingface.py`](https://github.com/samuelGabbai/P5_Futurisys/blob/main/scripts/publish_huggingface.py) ne copie
que quatre clés de l'artefact : `model`, `threshold`, `feature_names`, `positive_class`.
Le dictionnaire `records_by_employee_id` et toutes les autres clés sont exclus.
Le modèle original reste intact et continue à servir à l'import PostgreSQL local.

Seuls ces quatre fichiers sont envoyés à la racine du dépôt Model, sur sa branche `main` :

| Fichier | Contenu |
| --- | --- |
| `turnover_model.joblib` | Modèle et métadonnées d'inférence, sans dictionnaire de salariés |
| `metadata.json` | Commit Git source, SHA-256 de l'original et de l'export, variables, seuil et versions |
| `requirements.txt` | Versions des bibliothèques pour charger le modèle |
| `README.md` | Fiche modèle et exemple de chargement |

Ces quatre chemins sont mis à jour sur le dépôt distant. Les autres fichiers distants
ne sont ni envoyés ni supprimés. Les CSV, `.env`, journaux et fichiers PostgreSQL ne
font pas partie de l'export. L'exclusion des données source ne garantit pas, à elle seule,
l'anonymisation d'un modèle appris.

L'export préparé par le job de tests est conservé comme artefact GitHub
`huggingface-model-<commit>` pendant 14 jours. Le job de publication télécharge cet
artefact de la même exécution ; il vérifie son hash et son commit avant l'envoi.
Chaque publication porte le commit Git source dans son message de commit Hugging Face.
Le token n'est fourni qu'à l'étape de publication.

## Mise à jour du modèle

Exécuter l'entraînement et l'export du notebook, puis committer le nouveau fichier
`artifacts/turnover_model.joblib` et pousser sur `main`, directement ou via une PR.
La pipeline publie **l'artefact déjà entraîné présent dans le commit** : un changement
de code ne réentraîne pas automatiquement le modèle.

Cette configuration publie un dépôt **Model** ; elle ne déploie pas un Space et ne
redémarre pas une API déjà lancée. L'API locale et son import de salariés continuent
à utiliser l'artefact complet local. L'export Hugging Face a un autre hash et ne doit
pas remplacer l'original utilisé par `create_db.py`.

## Vérification locale sans publication

```bash
uv sync --locked --extra api --extra dev
uv run --no-sync python scripts/publish_huggingface.py \
  --prepare-only --git-sha COMMIT_SOURCE --output-dir hf-release
```

Le dossier de sortie doit être vide. Cette commande ne contacte pas Hugging Face.
Pour publier manuellement l'export après configuration de `HF_TOKEN` dans
l'environnement du terminal (`HF_REPO_ID` reste facultatif, avec la même valeur par défaut) :

```bash
uv sync --locked --extra publish
uv run --no-sync python scripts/publish_huggingface.py \
  --git-sha COMMIT_SOURCE --output-dir hf-release
```

Références : [upload de fichiers avec le client officiel](https://huggingface.co/docs/huggingface_hub/en/guides/upload)
et [droits des tokens Hugging Face](https://huggingface.co/docs/hub/security-tokens).
