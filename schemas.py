"""Contrats Pydantic partagés par les routes et le service d'inférence."""

import math
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    FiniteFloat,
    PositiveInt,
    ValidationInfo,
    model_validator,
)
from pydantic_core import PydanticCustomError


def numeric_value(value: Any) -> Any:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Une valeur numérique est requise ; booléens et valeurs nulles refusés.")
    return value


def binary_target(value: Any) -> int:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"0", "non"}:
            return 0
        if normalized in {"1", "oui"}:
            return 1
    elif type(value) is int and value in (0, 1):
        return value
    raise ValueError("La cible doit contenir 0/1 ou Non/Oui.")


NumericValue = Annotated[FiniteFloat, BeforeValidator(numeric_value)]
BinaryClass = Annotated[int, Field(strict=True, ge=0, le=1)]
BinaryTarget = Annotated[BinaryClass, BeforeValidator(binary_target)]
Probability = Annotated[FiniteFloat, Field(strict=True, ge=0, le=1)]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PredictionRequest(ApiModel):
    features: dict[str, NumericValue] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def match_model_features(cls, value: Any, info: ValidationInfo):
        expected = (info.context or {}).get("feature_names")
        supplied = value.get("features") if isinstance(value, dict) else None
        if expected is not None and isinstance(supplied, dict):
            missing = sorted(set(expected) - set(supplied))
            unexpected = sorted(set(supplied) - set(expected))
            if missing or unexpected:
                raise PydanticCustomError(
                    "feature_columns",
                    "Les variables ne correspondent pas au modèle.",
                    {"missing_features": missing, "unexpected_features": unexpected},
                )
        return value


class BatchPredictionRequest(ApiModel):
    rows: list[PredictionRequest] = Field(min_length=1)


class ScoreTargets(ApiModel):
    labels: list[BinaryTarget] = Field(min_length=1)


class PredictionResponse(ApiModel):
    probability: Probability
    threshold: Probability
    prediction: BinaryClass
    decision: Literal["Risque de départ élevé", "Risque de départ faible"]


class EmployeeScoreResponse(PredictionResponse):
    employee_id: PositiveInt


class FilePredictionResponse(ApiModel):
    row_count: PositiveInt
    predictions: list[BinaryClass] = Field(min_length=1)

    @model_validator(mode="after")
    def check_row_count(self):
        if len(self.predictions) != self.row_count:
            raise ValueError("Une prédiction est requise pour chaque ligne.")
        return self


class FileProbabilityResponse(ApiModel):
    row_count: PositiveInt
    classes: list[BinaryClass] = Field(min_length=2, max_length=2)
    probabilities: list[list[Probability]] = Field(min_length=1)

    @model_validator(mode="after")
    def check_probability_matrix(self):
        if set(self.classes) != {0, 1}:
            raise ValueError("Les classes doivent être 0 et 1, sans doublon.")
        if len(self.probabilities) != self.row_count:
            raise ValueError("Une ligne de probabilités est requise par entrée.")
        for row in self.probabilities:
            if len(row) != len(self.classes):
                raise ValueError("Une probabilité est requise pour chaque classe.")
            if not math.isclose(sum(row), 1.0, rel_tol=0, abs_tol=1e-6):
                raise ValueError("La somme des probabilités doit être égale à 1.")
        return self


class FileScoreResponse(ApiModel):
    row_count: PositiveInt
    score: Probability
    metric: Literal["accuracy"] = "accuracy"
    threshold: Probability
    threshold_accuracy: Probability
    threshold_precision: Probability
    threshold_recall: Probability
    threshold_f1: Probability


class HealthResponse(ApiModel):
    status: Literal["ok"]


class FeaturesResponse(ApiModel):
    features: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_features(self):
        if len(set(self.features)) != len(self.features):
            raise ValueError("Les noms de variables doivent être uniques.")
        return self


def public_validation_errors(error) -> list[dict]:
    """Localiser les erreurs sans recopier les valeurs RH ou les objets d'exception."""
    return [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in error.errors()[:20]
    ]
