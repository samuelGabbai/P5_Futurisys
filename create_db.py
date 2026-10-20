"""Créer la BDD et importer intégralement les trois CSV, de façon transactionnelle."""

import argparse
import hashlib
import json
import os
import re
from io import BytesIO
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url

from database import (
    Base,
    Employee,
    Evaluation,
    ModelVersion,
    PreparedEmployee,
    Survey,
    get_engine,
    session,
)

ROOT = Path(__file__).resolve().parent


def create_database():
    """Créer uniquement la base absente, avec un rôle autorisé à CREATE DATABASE."""
    url = make_url(os.environ["DATABASE_URL"])
    if not url.database or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", url.database):
        raise ValueError("Nom de base invalide.")
    admin_url = os.environ.get("DATABASE_ADMIN_URL") or url.set(database="postgres")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            ).scalar()
            if not exists:
                name = connection.dialect.identifier_preparer.quote(url.database)
                connection.execute(text(f"CREATE DATABASE {name}"))
    finally:
        admin.dispose()


def import_dataset(data_dir: Path, model_path: Path):
    sirh = pd.read_csv(data_dir / "extrait_sirh.csv", dtype={"id_employee": int})
    survey = pd.read_csv(data_dir / "extrait_sondage.csv", dtype={"code_sondage": str})
    evaluation = pd.read_csv(data_dir / "extrait_eval.csv", dtype={"eval_number": str})
    survey["employee_id"] = survey["code_sondage"].astype(int)
    evaluation["employee_id"] = (
        evaluation["eval_number"].str.extract(r"^(?:E_|EVAL-)(\d+)$")[0].astype(int)
    )
    ids = set(sirh["id_employee"])
    for frame, key in [(sirh, "id_employee"), (survey, "employee_id"), (evaluation, "employee_id")]:
        if frame[key].duplicated().any() or set(frame[key]) != ids:
            raise ValueError(
                "Identifiants dupliqués ou salariés non concordants dans les trois sources."
            )
        if frame.isna().any().any():
            raise ValueError("Valeurs manquantes : import annulé sans modification.")
    # Lire uniquement l'artefact local de confiance ; jamais de joblib téléversé.
    content = model_path.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    bundle = joblib.load(BytesIO(content))
    prepared = bundle["records_by_employee_id"]
    if {int(key) for key in prepared} != ids:
        raise ValueError("Les variables préparées ne couvrent pas exactement le dataset complet.")
    expected = bundle["feature_names"]
    for values in prepared.values():
        if (
            set(values) != set(expected)
            or not np.isfinite([float(values[key]) for key in expected]).all()
        ):
            raise ValueError("Variables préparées invalides.")
    with session() as db, db.begin():
        # Une réimportation identique met à jour les sources sans supprimer les journaux.
        for values in sirh.to_dict(orient="records"):
            db.merge(Employee(**values))
        db.flush()
        for model, frame in [(Survey, survey), (Evaluation, evaluation)]:
            for values in frame.to_dict(orient="records"):
                db.merge(model(**values))
        db.merge(
            ModelVersion(
                sha256=sha,
                feature_names=expected,
                threshold=float(bundle["threshold"]),
                positive_class=int(bundle["positive_class"]),
            )
        )
        db.flush()
        for employee_id, values in prepared.items():
            db.merge(
                PreparedEmployee(
                    employee_id=int(employee_id),
                    model_sha256=sha,
                    features={key: float(values[key]) for key in expected},
                )
            )
    with session() as db:
        return {
            model.__tablename__: db.scalar(select(func.count()).select_from(model))
            for model in [Employee, Survey, Evaluation, PreparedEmployee]
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-database", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "Data")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path(os.environ.get("HRNOVA_MODEL_PATH", ROOT / "artifacts/turnover_model.joblib")),
    )
    args = parser.parse_args()
    if args.create_database:
        create_database()
    Base.metadata.create_all(get_engine())
    with get_engine().begin() as connection:
        connection.exec_driver_sql((ROOT / "docs/migrations/002_explicit_api_logs.sql").read_text())
    print(json.dumps(import_dataset(args.data_dir, args.model_path), indent=2))


if __name__ == "__main__":
    main()
