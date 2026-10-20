"""API de prédiction du risque de départ HRNova."""

import csv
import hashlib
import logging
import math
import os
from functools import lru_cache
from io import BytesIO, StringIO
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

import audit
import inference

DEFAULT_MODEL_PATH = Path(__file__).parent / "artifacts" / "turnover_model.joblib"
MAX_CSV_BYTES = 10 * 1024 * 1024
TARGET_COLUMN = "a_quitte_l_entreprise"

app = FastAPI(
    title="HRNova Turnover API",
    description="Prédit le risque de départ à partir des variables préparées du modèle HRNova.",
    version="1.0.0",
)
logger = logging.getLogger(__name__)


@app.exception_handler(StarletteHTTPException)
async def trace_http_error(request: Request, error: StarletteHTTPException):
    detail = error.detail
    if isinstance(detail, dict) and "missing_features" in detail:
        message = (
            f"Colonnes manquantes : {', '.join(detail['missing_features']) or 'aucune'} ; "
            f"colonnes inattendues : {', '.join(detail['unexpected_features']) or 'aucune'}."
        )
    else:
        message = str(detail)
    request.state.audit_error = {"message": audit.redact(message), "detail": detail}
    return await http_exception_handler(request, error)


@app.exception_handler(RequestValidationError)
async def trace_validation_error(request: Request, error: RequestValidationError):
    # Ne pas recopier input, ctx ou le corps JSON dans le journal des erreurs.
    errors = [
        {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    request.state.audit_error = {
        "message": "Requête invalide : "
        + "; ".join(
            f"{'.'.join(map(str, item['location']))} : {item['message']}" for item in errors
        ),
        "validation_errors": errors,
    }
    request.state.audit_error_type = "RequestValidationError"
    return await request_validation_exception_handler(request, error)


@app.middleware("http")
async def trace_exchange(request: Request, call_next):
    started = perf_counter()
    exchange_id = str(uuid4())
    request.state.exchange_id = exchange_id
    request.state.audit_details = {
        "client_host": request.client.host if request.client else None,
        "query": {
            key: request.query_params[key][:255]
            for key in ("separator", "target_column")
            if key in request.query_params
        },
    }
    try:
        await run_in_threadpool(
            audit.start_exchange,
            exchange_id,
            request.method,
            request.url.path,
            request.state.audit_details,
        )
    except (SQLAlchemyError, RuntimeError):
        logger.error("BDD indisponible au début de la requête %s", exchange_id)
        return JSONResponse(
            status_code=503,
            content={"detail": "Base de données indisponible."},
            headers={"X-Request-ID": exchange_id},
        )
    error_type = None
    try:
        response = await call_next(request)
    except Exception as error:
        error_type = type(error).__name__
        request.state.audit_error = audit.exception_details(error)
        logger.error("Échec de la requête %s (%s)", exchange_id, error_type)
        status = 503 if isinstance(error, SQLAlchemyError) else 500
        response = JSONResponse(
            status_code=status,
            content={"detail": "Échec de la requête ; consultez le journal local."},
        )
    try:
        route = request.scope.get("route")
        request.state.audit_details.update(
            {
                "route_template": getattr(route, "path", request.url.path)[:255],
                "path_parameters": {
                    key: value for key, value in request.path_params.items() if key == "employee_id"
                },
            }
        )
        await run_in_threadpool(
            audit.finish_exchange,
            exchange_id,
            response.status_code,
            (perf_counter() - started) * 1000,
            request.state.audit_details,
            error_type or getattr(request.state, "audit_error_type", None),
            getattr(request.state, "audit_error", None),
        )
    except (SQLAlchemyError, RuntimeError):
        logger.error("Impossible de finaliser le journal de la requête %s", exchange_id)
        response = JSONResponse(
            status_code=503, content={"detail": "Enregistrement de la requête incomplet."}
        )
    response.headers["X-Request-ID"] = exchange_id
    return response


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


def _uploaded_frame(
    request: Request, file: UploadFile, separator: str, target_column: str | None = None
) -> pd.DataFrame:
    request.state.audit_details.update(
        {
            "filename": (file.filename or "")[:255],
            "file_size_bytes": file.size,
            "content_type": file.content_type,
            "separator": separator,
        }
    )
    if target_column is not None:
        request.state.audit_details["target_column"] = target_column
    frame = _read_csv(file, separator)
    request.state.audit_details.update(
        {"uploaded_rows": len(frame), "uploaded_columns": len(frame.columns)}
    )
    return frame


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
        raise HTTPException(
            status_code=422, detail="Les variables doivent être numériques."
        ) from error
    if not np.isfinite(numeric.to_numpy()).all():
        raise HTTPException(status_code=422, detail="Valeurs manquantes ou non finies dans le CSV.")
    return numeric


@app.post("/predict/file", response_model=FilePredictionResponse, tags=["Fichiers CSV"])
def predict_file(request: Request, file: UploadFile, separator: str = Query(",", pattern="^[,;]$")):
    """Prédictions natives du modèle, dans l'ordre des lignes du CSV."""
    frame = _uploaded_frame(request, file, separator)
    artifact = get_model_bundle()
    features = _file_features(frame, artifact)
    return inference.execute(
        request.state.exchange_id, "predict", features, artifact, filename=file.filename
    )


@app.post("/predict-proba/file", response_model=FileProbabilityResponse, tags=["Fichiers CSV"])
def predict_proba_file(
    request: Request, file: UploadFile, separator: str = Query(",", pattern="^[,;]$")
):
    """Probabilités par classe ; classes donne l'ordre des colonnes de probabilités."""
    frame = _uploaded_frame(request, file, separator)
    artifact = get_model_bundle()
    features = _file_features(frame, artifact)
    return inference.execute(
        request.state.exchange_id, "predict_proba", features, artifact, filename=file.filename
    )


@app.post("/score/file", response_model=FileScoreResponse, tags=["Fichiers CSV"])
def score_file(
    request: Request,
    file: UploadFile,
    target_column: str = Query(TARGET_COLUMN),
    separator: str = Query(",", pattern="^[,;]$"),
):
    """Accuracy native et métriques au seuil optimisé, avec les vraies réponses."""
    frame = _uploaded_frame(request, file, separator, target_column)
    artifact = get_model_bundle()
    if target_column in artifact["feature_names"]:
        raise HTTPException(
            status_code=422, detail="La cible ne peut pas être une variable du modèle."
        )
    if target_column not in frame:
        raise HTTPException(status_code=422, detail=f"Colonne cible requise : {target_column}.")
    labels = frame.pop(target_column).str.strip().str.lower().replace({"non": "0", "oui": "1"})
    if not labels.isin(["0", "1"]).all():
        raise HTTPException(status_code=422, detail="La cible doit contenir 0/1 ou Non/Oui.")
    labels = labels.astype(int)
    features = _file_features(frame, artifact)
    return inference.execute(
        request.state.exchange_id,
        "score",
        features,
        artifact,
        labels=labels,
        filename=file.filename,
    )


@lru_cache(maxsize=1)
def _load_artifact(model_path: str) -> dict[str, Any]:
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    content = path.read_bytes()
    artifact = joblib.load(BytesIO(content))
    required_keys = {
        "model",
        "threshold",
        "feature_names",
        "positive_class",
    }
    if not isinstance(artifact, dict) or not required_keys.issubset(artifact):
        raise ValueError("Artefact invalide : clés requises absentes.")
    artifact["model_sha256"] = hashlib.sha256(content).hexdigest()
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
def predict(request: Request, payload: PredictionRequest) -> PredictionResponse:
    artifact = get_model_bundle()
    return _score_features(payload.features, artifact, request.state.exchange_id)


def _score_features(
    supplied_features: dict[str, Any], artifact: dict[str, Any], exchange_id: str
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
        raise HTTPException(
            status_code=422, detail="Toutes les variables doivent être numériques."
        ) from error
    if not all(math.isfinite(value) for value in row.values()):
        raise HTTPException(status_code=422, detail="Les variables doivent être des nombres finis.")

    input_frame = pd.DataFrame([row], columns=expected_features)
    return PredictionResponse(
        **inference.execute(exchange_id, "threshold_predict", input_frame, artifact)
    )


@app.get("/employees/{employee_id}/score", response_model=EmployeeScoreResponse)
def score_employee(employee_id: int, request: Request) -> EmployeeScoreResponse:
    artifact = get_model_bundle()
    employee_values = inference.employee_features(employee_id, artifact)
    frame = _file_features(pd.DataFrame([employee_values]), artifact)
    score = inference.execute(
        request.state.exchange_id, "threshold_predict", frame, artifact, employee_id=employee_id
    )
    return EmployeeScoreResponse(**score)
