"""Préparer un export sans lignes salariées, puis publier cet export sur le Model Hub."""

import argparse
import hashlib
import json
import math
import os
from importlib.metadata import version
from io import BytesIO
from pathlib import Path

import joblib

MODEL_FILE = "turnover_model.joblib"
PUBLIC_KEYS = {"model", "threshold", "feature_names", "positive_class"}
RELEASE_FILES = {MODEL_FILE, "metadata.json", "README.md", "requirements.txt"}
DEFAULT_REPO_ID = "SamGabb/hrnova"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def prepare_release(model_path: Path, output_dir: Path, git_sha: str) -> dict:
    if not git_sha.strip():
        raise ValueError("Le commit Git source doit être renseigné.")
    # L'artefact provient du dépôt local de confiance, jamais d'un upload utilisateur.
    content = model_path.read_bytes()
    bundle = joblib.load(BytesIO(content))
    if not isinstance(bundle, dict) or not PUBLIC_KEYS.issubset(bundle):
        raise ValueError("L'artefact doit contenir le modèle et ses métadonnées.")
    features = bundle["feature_names"]
    if (
        not isinstance(features, list)
        or not features
        or not all(isinstance(name, str) and name for name in features)
        or len(set(features)) != len(features)
    ):
        raise ValueError("Noms de variables invalides.")
    model = bundle["model"]
    if not all(
        callable(getattr(model, method, None)) for method in ("predict", "predict_proba", "score")
    ):
        raise ValueError("Le modèle doit exposer predict, predict_proba et score.")
    threshold = float(bundle["threshold"])
    positive = int(bundle["positive_class"])
    classes = [int(value) for value in model.classes_]
    if (
        not math.isfinite(threshold)
        or not 0 <= threshold <= 1
        or set(classes) != {0, 1}
        or positive not in classes
    ):
        raise ValueError("Seuil ou classes invalides.")
    if output_dir.resolve() == model_path.resolve().parent:
        raise ValueError("L'export doit utiliser un dossier distinct de l'artefact source.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError(
            "Le dossier d'export doit être vide pour éviter toute publication parasite."
        )
    public_bundle = {
        "model": model,
        "threshold": threshold,
        "feature_names": features,
        "positive_class": positive,
    }
    joblib.dump(public_bundle, output_dir / MODEL_FILE, compress=3)
    requirements = {
        name: version(name) for name in ("scikit-learn", "numpy", "scipy", "pandas", "joblib")
    }
    metadata = {
        "git_sha": git_sha,
        "source_sha256": sha256(content),
        "model_sha256": sha256((output_dir / MODEL_FILE).read_bytes()),
        "feature_names": features,
        "threshold": threshold,
        "positive_class": positive,
        "classes": classes,
        "versions": requirements,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "requirements.txt").write_text(
        "".join(f"{name}=={release}\n" for name, release in requirements.items()), encoding="utf-8"
    )
    (output_dir / "README.md").write_text(
        "---\nlanguage: fr\nlibrary_name: sklearn\ntags:\n- tabular-classification\n- hrnova\n---\n\n"
        "# HRNova — Modèle de turnover\n\n"
        f"Export du commit Git `{git_sha}`. Classification binaire : 0 = resté, 1 = quitté.\n\n"
        "Le fichier `turnover_model.joblib` contient le modèle calibré, le seuil optimisé, "
        "les noms des variables et la classe positive. Les lignes individuelles "
        "`records_by_employee_id`, le dataset, la BDD et les logs sont exclus de l'export.\n\n"
        "Les inputs doivent être numériques, préparés et encodés comme dans le notebook. "
        "Les versions des bibliothèques sont enregistrées dans `requirements.txt`. "
        "Charger uniquement un artefact joblib provenant d'une source de confiance.\n\n"
        "```python\nimport joblib\nfrom huggingface_hub import hf_hub_download\n\n"
        f'path = hf_hub_download(repo_id="{DEFAULT_REPO_ID}", filename="turnover_model.joblib")\n'
        "bundle = joblib.load(path)\n# X : DataFrame numérique avec les colonnes de bundle['feature_names']\n"
        "# predictions = bundle['model'].predict(X[bundle['feature_names']])\n"
        "# probabilities = bundle['model'].predict_proba(X[bundle['feature_names']])\n"
        "# score = bundle['model'].score(X[bundle['feature_names']], y)\n```\n\n"
        "L'upload versionne un modèle déjà entraîné. Il ne lance ni entraînement ni serveur API. "
        "La suppression des lignes source n'est pas une garantie d'anonymisation du modèle appris.\n",
        encoding="utf-8",
    )
    return metadata


def publish_release(output_dir: Path, repo_id: str, token: str, git_sha: str, client=None):
    if not token.strip() or len(repo_id.split("/")) != 2 or not all(repo_id.split("/")):
        raise ValueError("HF_TOKEN et HF_REPO_ID (compte/depot) doivent être configurés.")
    if {path.name for path in output_dir.iterdir()} != RELEASE_FILES or any(
        not (output_dir / name).is_file() or (output_dir / name).is_symlink()
        for name in RELEASE_FILES
    ):
        raise ValueError("L'export doit contenir uniquement les quatre fichiers autorisés.")
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    if not git_sha or metadata["git_sha"] != git_sha:
        raise ValueError("Le commit de l'export diffère du commit à publier.")
    if sha256((output_dir / MODEL_FILE).read_bytes()) != metadata["model_sha256"]:
        raise ValueError("Le fichier modèle a changé depuis sa préparation.")
    if client is None:
        from huggingface_hub import HfApi

        client = HfApi(token=token)
    # Le dépôt Model doit déjà exister ; sa visibilité est choisie par l'utilisateur.
    return client.upload_folder(
        repo_id=repo_id,
        repo_type="model",
        revision="main",
        folder_path=str(output_dir),
        allow_patterns=sorted(RELEASE_FILES),
        commit_message=f"Modèle HRNova — Git {git_sha}",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--model-path", type=Path, default=Path("artifacts") / MODEL_FILE)
    parser.add_argument("--output-dir", type=Path, default=Path("hf-release"))
    parser.add_argument("--git-sha", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()
    if args.prepare_only:
        metadata = prepare_release(args.model_path, args.output_dir, args.git_sha)
        print(f"Export préparé : {metadata['model_sha256']} (commit {metadata['git_sha']}).")
    else:
        repo_id = os.environ.get("HF_REPO_ID") or DEFAULT_REPO_ID
        publish_release(
            args.output_dir,
            repo_id,
            os.environ.get("HF_TOKEN", ""),
            args.git_sha,
        )
        print(f"Modèle publié : https://huggingface.co/{repo_id}")


if __name__ == "__main__":
    main()
