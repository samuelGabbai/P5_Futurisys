"""API de prédiction du risque de départ HRNova."""

import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

DEFAULT_MODEL_PATH = Path(__file__).parent / "artifacts" / "turnover_model.joblib"

app = FastAPI(
    title="HRNova Turnover API",
    description="Prédit le risque de départ à partir des variables préparées du modèle HRNova.",
    version="1.0.0",
)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: dict[str, Any]


class PredictionResponse(BaseModel):
    probability: float
    threshold: float
    prediction: int
    decision: str


class EmployeeScoreResponse(PredictionResponse):
    employee_id: int


@lru_cache(maxsize=1)
def _load_artifact(model_path: str) -> dict[str, Any]:
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    artifact = joblib.load(path)
    required_keys = {
        "model",
        "threshold",
        "feature_names",
        "positive_class",
        "records_by_employee_id",
    }
    if not isinstance(artifact, dict) or not required_keys.issubset(artifact):
        raise ValueError("Artefact invalide : clés requises absentes.")
    return artifact


def get_model_bundle() -> dict[str, Any]:
    model_path = os.environ.get("HRNOVA_MODEL_PATH", str(DEFAULT_MODEL_PATH))
    try:
        return _load_artifact(model_path)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Modèle indisponible. Exécutez la cellule d'export du notebook.",
        ) from error
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(status_code=500, detail="Artefact de modèle invalide.") from error


@app.get("/health")
def health() -> dict[str, str]:
    get_model_bundle()
    return {"status": "ok"}


@app.get("/features")
def features() -> dict[str, list[str]]:
    return {"features": get_model_bundle()["feature_names"]}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest) -> PredictionResponse:
    artifact = get_model_bundle()
    return _score_features(request.features, artifact)


def _score_features(
    supplied_features: dict[str, Any], artifact: dict[str, Any]
) -> PredictionResponse:
    expected_features = artifact["feature_names"]

    missing = sorted(set(expected_features) - set(supplied_features))
    unexpected = sorted(set(supplied_features) - set(expected_features))
    if missing or unexpected:
        raise HTTPException(
            status_code=422,
            detail={"missing_features": missing, "unexpected_features": unexpected},
        )

    try:
        row = {name: float(supplied_features[name]) for name in expected_features}
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Toutes les variables doivent être numériques.") from error
    if not all(math.isfinite(value) for value in row.values()):
        raise HTTPException(status_code=422, detail="Les variables doivent être des nombres finis.")

    model = artifact["model"]
    classes = list(model.classes_)
    positive_class = artifact["positive_class"]
    if positive_class not in classes:
        raise HTTPException(status_code=500, detail="Classe positive absente du modèle.")

    input_frame = pd.DataFrame([row], columns=expected_features)
    probability = float(model.predict_proba(input_frame)[0][classes.index(positive_class)])
    threshold = float(artifact["threshold"])
    prediction = int(probability >= threshold)

    return PredictionResponse(
        probability=probability,
        threshold=threshold,
        prediction=prediction,
        decision="Risque de départ élevé" if prediction else "Risque de départ faible",
    )


@app.get("/employees/{employee_id}/score", response_model=EmployeeScoreResponse)
def score_employee(employee_id: int) -> EmployeeScoreResponse:
    artifact = get_model_bundle()
    records = artifact["records_by_employee_id"]
    employee_features = records.get(str(employee_id))
    if employee_features is None:
        raise HTTPException(status_code=404, detail="Identifiant salarié introuvable.")

    score = _score_features(employee_features, artifact)
    return EmployeeScoreResponse(employee_id=employee_id, **score.model_dump())