"""Messages et métadonnées lisibles des échanges HTTP, sans corps ni identifiants secrets."""

import re
from collections import Counter

from sqlalchemy.exc import SQLAlchemyError

from database import ApiExchange, ModelOutput, session, utc_now


def redact(message: str) -> str:
    message = re.sub(r"(\w+(?:\+\w+)?://[^\s:/]+:)[^@\s]+@", r"\1[masqué]@", message)
    message = re.sub(
        r"(?i)((?:password|passwd|token|secret|authorization)\s*[:=]\s*)[^\s,;]+",
        r"\1[masqué]",
        message,
    )
    return message.replace("\n", " ")[:2000]


def exception_details(error: Exception) -> dict:
    if isinstance(error, SQLAlchemyError):
        # str(error) peut contenir la requête SQL et les valeurs RH liées.
        return {
            "type": type(error).__name__,
            "message": "Échec d'accès ou d'écriture PostgreSQL.",
            "sqlstate": getattr(getattr(error, "orig", None), "sqlstate", None),
        }
    return {"type": type(error).__name__, "message": redact(str(error))}


def start_exchange(exchange_id: str, method: str, endpoint: str, details: dict):
    with session() as db, db.begin():
        db.add(
            ApiExchange(
                id=exchange_id,
                method=method,
                endpoint=endpoint[:255],
                request_details=details,
                processing_stage="received",
            )
        )


def finish_exchange(
    exchange_id: str,
    status: int,
    duration_ms: float,
    details: dict,
    error_type: str | None = None,
    error_details: dict | None = None,
):
    with session() as db, db.begin():
        exchange = db.get(ApiExchange, exchange_id)
        exchange.http_status = status
        exchange.completed_at = utc_now()
        exchange.duration_ms = round(duration_ms, 3)
        exchange.status = (
            "failed" if status >= 500 else "rejected" if status >= 400 else "succeeded"
        )
        exchange.error_type = error_type or (f"HTTP_{status}" if status >= 400 else None)
        exchange.error_details = error_details
        exchange.request_details = {**(exchange.request_details or {}), **details}
        if details.get("filename"):
            exchange.filename = details["filename"][:255]
        if status < 400:
            exchange.processing_stage = "completed"
            output = db.get(ModelOutput, exchange_id)
            if output:
                payload = output.payload
                summary = {
                    key: value
                    for key, value in payload.items()
                    if key not in {"predictions", "probabilities"}
                }
                if "predictions" in payload:
                    summary["prediction_counts"] = dict(
                        Counter(str(v) for v in payload["predictions"])
                    )
                exchange.response_summary = summary
            exchange.message = (
                f"{exchange.operation} terminé : {exchange.row_count} ligne(s), "
                f"{exchange.feature_count} variable(s) ; entrées et sorties enregistrées."
                if output
                else f"{exchange.method} {exchange.endpoint} : requête traitée avec succès."
            )
        else:
            reason = (error_details or {}).get("message", f"Erreur HTTP {status}")
            exchange.message = redact(
                f"{exchange.method} {exchange.endpoint} : {reason} (étape : {exchange.processing_stage})."
            )
