"""API de prédiction du risque de départ HRNova."""

import csv
import math
import os
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

DEFAULT_MODEL_PATH = Path(__file__).parent / "artifacts" / "turnover_model.joblib"
MAX_CSV_BYTES = 10 * 1024 * 1024
TARGET_COLUMN = "a_quitte_l_entreprise"

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


class FilePredictionResponse(BaseModel):
    row_count: int
    predictions: list[int]


class FileProbabilityResponse(BaseModel):
    row_count: int
    classes: list[int]
    probabilities: list[list[float]]


class FileScoreResponse(BaseModel):
    row_count: int
    score: float
    metric: str = "accuracy"
    threshold: float
    threshold_accuracy: float
    threshold_precision: float
    threshold_recall: float
    threshold_f1: float


def _read_csv(file: UploadFile, separator: str) -> pd.DataFrame:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Envoyez un fichier .csv.")
    content = file.file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="Le fichier dépasse la limite de 10 Mio.")
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(StringIO(text), delimiter=separator, strict=True))
        rows = [row for row in rows if row]
        if len(rows) < 2:
            raise ValueError("Aucune ligne de données.")
        header = rows[0]
        if any(not name.strip() for name in header) or len(set(header)) != len(header):
            raise ValueError("Les noms de colonnes doivent être renseignés et uniques.")
        if any(len(row) != len(header) for row in rows[1:]):
            raise ValueError("Le nombre de champs doit être identique sur chaque ligne.")
        return pd.DataFrame(rows[1:], columns=header)
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        raise HTTPException(status_code=422, detail=f"CSV UTF-8 invalide : {error}") from error


def _file_features(frame: pd.DataFrame, artifact: dict[str, Any]) -> pd.DataFrame:
    expected = artifact["feature_names"]
    missing = sorted(set(expected) - set(frame.columns))
    unexpected = sorted(set(frame.columns) - set(expected))
    if missing or unexpected:
        raise HTTPException(
            status_code=422,
            detail={"missing_features": missing, "unexpected_features": unexpected},
        )
    try:
        numeric = frame.loc[:, expected].apply(pd.to_numeric, errors="raise").astype(float)
    except (TypeError, ValueError, OverflowError) as error:
        raise HTTPException(status_code=422, detail="Les variables doivent être numériques.") from error
    if not np.isfinite(numeric.to_numpy()).all():
        raise HTTPException(status_code=422, detail="Valeurs manquantes ou non finies dans le CSV.")
    return numeric


@app.post("/predict/file", response_model=FilePredictionResponse, tags=["Fichiers CSV"])
def predict_file(file: UploadFile, separator: str = Query(",", pattern="^[,;]$")):
    """Prédictions natives du modèle, dans l'ordre des lignes du CSV."""
    artifact = get_model_bundle()
    features = _file_features(_read_csv(file, separator), artifact)
    return FilePredictionResponse(
        row_count=len(features), predictions=artifact["model"].predict(features).tolist()
    )


@app.post("/predict-proba/file", response_model=FileProbabilityResponse, tags=["Fichiers CSV"])
def predict_proba_file(file: UploadFile, separator: str = Query(",", pattern="^[,;]$")):
    """Probabilités par classe ; classes donne l'ordre des colonnes de probabilités."""
    artifact = get_model_bundle()
    features = _file_features(_read_csv(file, separator), artifact)
    return FileProbabilityResponse(
        row_count=len(features),
        classes=list(artifact["model"].classes_),
        probabilities=np.asarray(artifact["model"].predict_proba(features)).tolist(),
    )


@app.post("/score/file", response_model=FileScoreResponse, tags=["Fichiers CSV"])
def score_file(
    file: UploadFile,
    target_column: str = Query(TARGET_COLUMN),
    separator: str = Query(",", pattern="^[,;]$"),
):
    """Accuracy native et métriques au seuil optimisé, avec les vraies réponses."""
    artifact = get_model_bundle()
    frame = _read_csv(file, separator)
    if target_column in artifact["feature_names"]:
        raise HTTPException(status_code=422, detail="La cible ne peut pas être une variable du modèle.")
    if target_column not in frame:
        raise HTTPException(status_code=422, detail=f"Colonne cible requise : {target_column}.")
    labels = frame.pop(target_column).str.strip().str.lower().replace({"non": "0", "oui": "1"})
    if not labels.isin(["0", "1"]).all():
        raise HTTPException(status_code=422, detail="La cible doit contenir 0/1 ou Non/Oui.")
    labels = labels.astype(int)
    features = _file_features(frame, artifact)
    model = artifact["model"]
    classes = list(model.classes_)
    positive = artifact["positive_class"]
    if set(classes) != {0, 1} or positive not in classes:
        raise HTTPException(status_code=500, detail="Le score requiert un modèle binaire 0/1.")
    probability = np.asarray(model.predict_proba(features))[:, classes.index(positive)]
    threshold = float(artifact["threshold"])
    negative = next(value for value in classes if value != positive)
    predictions = np.where(probability >= threshold, positive, negative)
    return FileScoreResponse(
        row_count=len(features),
        score=float(model.score(features, labels)),
        threshold=threshold,
        threshold_accuracy=float(accuracy_score(labels, predictions)),
        threshold_precision=float(precision_score(labels, predictions, pos_label=positive, zero_division=0)),
        threshold_recall=float(recall_score(labels, predictions, pos_label=positive, zero_division=0)),
        threshold_f1=float(f1_score(labels, predictions, pos_label=positive, zero_division=0)),
    )


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
