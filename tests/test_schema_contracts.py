"""Cas limites des contrats : cibles, classes et cohérence des réponses."""

import pytest
from pydantic import ValidationError

from schemas import FeaturesResponse, FileProbabilityResponse, ScoreTargets


def test_integer_targets_are_supported_without_conversion_to_boolean():
    assert ScoreTargets(labels=[0, 1]).labels == [0, 1]


@pytest.mark.parametrize("labels", [[True], [False], [2], [-1], [0.5], [None], ["maybe"]])
def test_invalid_targets_are_rejected(labels):
    with pytest.raises(ValidationError):
        ScoreTargets(labels=labels)


@pytest.mark.parametrize(
    "classes,probabilities,row_count,message",
    [
        ([0, 0], [[0.5, 0.5]], 1, "sans doublon"),
        ([0, 1], [[0.5, 0.5]], 2, "par entrée"),
    ],
)
def test_probability_response_requires_unique_classes_and_matching_rows(
    classes, probabilities, row_count, message
):
    with pytest.raises(ValidationError, match=message):
        FileProbabilityResponse(classes=classes, probabilities=probabilities, row_count=row_count)


def test_duplicate_feature_names_are_rejected():
    with pytest.raises(ValidationError, match="uniques"):
        FeaturesResponse(features=["age", "age"])
