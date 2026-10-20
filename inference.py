"""Seul point d'appel du modèle : écrire, relire, calculer, enregistrer, relire."""

import json
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sqlalchemy import select

from database import ApiExchange, ModelInput, ModelOutput, ModelVersion, PreparedEmployee, session


def employee_features(employee_id: int, artifact: dict) -> dict:
    with session() as db:
        record = db.get(PreparedEmployee, (employee_id, artifact["model_sha256"]))
        if record is None:
            raise HTTPException(
                status_code=404, detail="Salarié absent des variables préparées en BDD."
            )
        return record.features


def execute(
    exchange_id: str,
    operation: str,
    features: pd.DataFrame,
    artifact: dict[str, Any],
    labels: pd.Series | None = None,
    employee_id: int | None = None,
    filename: str | None = None,
) -> dict:
    """Aucun calcul n'est possible avant le commit et la relecture des inputs."""
    sha = artifact["model_sha256"]
    with session() as db, db.begin():
        version = db.get(ModelVersion, sha)
        if version is None:
            raise HTTPException(
                status_code=503, detail="Modèle non enregistré : relancez create_db.py."
            )
        if (
            version.feature_names != artifact["feature_names"]
            or version.threshold != float(artifact["threshold"])
            or version.positive_class != int(artifact["positive_class"])
        ):
            raise HTTPException(status_code=503, detail="Métadonnées du modèle incohérentes.")
        exchange = db.get(ApiExchange, exchange_id)
        exchange.model_sha256 = sha
        exchange.operation = operation
        exchange.filename = filename[:255] if filename else None
        exchange.row_count = len(features)
        exchange.feature_count = len(features.columns)
        exchange.processing_stage = "inputs_saved"
        db.add_all(
            [
                ModelInput(
                    exchange_id=exchange_id,
                    row_index=index,
                    employee_id=employee_id,
                    features=values,
                    target=int(labels.iloc[index]) if labels is not None else None,
                )
                for index, values in enumerate(features.to_dict(orient="records"))
            ]
        )

    # Nouvelle session : les données réellement fournies au modèle proviennent du SELECT.
    with session() as db:
        stored = db.scalars(
            select(ModelInput)
            .where(ModelInput.exchange_id == exchange_id)
            .order_by(ModelInput.row_index)
        ).all()
        frame = pd.DataFrame([row.features for row in stored], columns=artifact["feature_names"])
        truth = pd.Series([row.target for row in stored]) if labels is not None else None
        db.get(ApiExchange, exchange_id).processing_stage = "model_running"
        db.commit()
    result, model_values = _calculate(operation, frame, truth, artifact)
    if employee_id is not None:
        result["employee_id"] = employee_id
    payload = json.loads(json.dumps(result, allow_nan=False))
    model_values = json.loads(json.dumps(model_values, allow_nan=False))

    with session() as db, db.begin():
        db.add(ModelOutput(exchange_id=exchange_id, payload=payload, model_values=model_values))
        db.get(ApiExchange, exchange_id).processing_stage = "outputs_saved"
    # La réponse HTTP provient à son tour de la sortie persistée.
    with session() as db:
        return db.get(ModelOutput, exchange_id).payload


def _calculate(
    operation: str, frame: pd.DataFrame, truth: pd.Series | None, artifact: dict
) -> tuple[dict, dict]:
    model = artifact["model"]
    if operation == "predict":
        predictions = np.asarray(model.predict(frame)).astype(int).tolist()
        return {"row_count": len(frame), "predictions": predictions}, {"predict": predictions}
    classes = [int(value) for value in model.classes_]
    positive = int(artifact["positive_class"])
    if set(classes) != {0, 1} or positive not in classes:
        raise HTTPException(status_code=500, detail="Le modèle doit être binaire 0/1.")
    probabilities = np.asarray(model.predict_proba(frame))
    model_values = {"classes": classes, "predict_proba": probabilities.tolist()}
    if operation == "predict_proba":
        return {
            "row_count": len(frame),
            "classes": classes,
            "probabilities": probabilities.tolist(),
        }, model_values
    threshold = float(artifact["threshold"])
    probability = probabilities[:, classes.index(positive)]
    predictions = np.where(probability >= threshold, positive, 1 - positive)
    if operation == "score":
        model_values["score"] = float(model.score(frame, truth))
        return {
            "row_count": len(frame),
            "score": model_values["score"],
            "metric": "accuracy",
            "threshold": threshold,
            "threshold_accuracy": float(accuracy_score(truth, predictions)),
            "threshold_precision": float(
                precision_score(truth, predictions, pos_label=positive, zero_division=0)
            ),
            "threshold_recall": float(
                recall_score(truth, predictions, pos_label=positive, zero_division=0)
            ),
            "threshold_f1": float(
                f1_score(truth, predictions, pos_label=positive, zero_division=0)
            ),
        }, model_values
    if operation == "threshold_predict":
        prediction = int(predictions[0])
        return {
            "probability": float(probability[0]),
            "threshold": threshold,
            "prediction": prediction,
            "decision": (
                "Risque de départ élevé" if prediction == positive else "Risque de départ faible"
            ),
        }, model_values
    raise ValueError(f"Opération inconnue : {operation}")
