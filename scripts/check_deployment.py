"""Contrôle en lecture seule de la compatibilité BDD / modèle avant déploiement."""

import hashlib
import os
import sys
from pathlib import Path

# Exécutable dans l'image sans dépendre du répertoire courant de Python.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
from sqlalchemy import select

from database import ModelVersion, session


def check():
    path = Path(os.environ["HRNOVA_MODEL_PATH"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    bundle = joblib.load(path)
    with session() as db:
        version = db.get(ModelVersion, digest)
        if version is None:
            raise ValueError("Version du modèle absente de la base cible : initialiser la base.")
        if (
            version.feature_names != bundle["feature_names"]
            or version.threshold != float(bundle["threshold"])
            or version.positive_class != int(bundle["positive_class"])
        ):
            raise ValueError("Métadonnées du modèle incompatibles avec la base cible.")
        # Vérifier aussi que le rôle peut consulter les tables de traçabilité.
        from database import ApiExchange, ModelInput, ModelOutput

        for model in (ApiExchange, ModelInput, ModelOutput):
            db.execute(select(model).limit(0))
    print(f"Base cible accessible, modèle enregistré : {digest}")


if __name__ == "__main__":
    try:
        check()
    except Exception:
        # Les exceptions SQL peuvent contenir des paramètres de connexion ou des données.
        print(
            "Précontrôle échoué : vérifier la base, les droits, le schéma et la version du modèle.",
            file=sys.stderr,
        )
        sys.exit(1)
