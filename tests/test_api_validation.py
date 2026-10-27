"""Contrôles de chaque route et des données fournies au modèle ou retournées par lui."""

import numpy as np
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

import api
from database import ApiExchange, ModelInput, ModelOutput, session
from test_api import client_with_fake_model, upload

CSV_ROUTES = ["/predict/file", "/predict-proba/file", "/score/file"]


def assert_no_inference_output(response):
    with session() as db:
        exchange_id = response.headers["X-Request-ID"]
        assert db.get(ModelOutput, exchange_id) is None


@pytest.mark.parametrize("value", [True, False, None, [], {}, "text", "nan", "inf", "1e9999"])
def test_predict_rejects_invalid_numeric_values_before_inference(monkeypatch, value):
    response = client_with_fake_model(monkeypatch).post(
        "/predict",
        json={"features": {"feature_a": value, "feature_b": 4}},
    )
    assert response.status_code == 422
    assert_no_inference_output(response)
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 0


def test_nonstandard_json_nan_is_rejected_without_serialization_failure(monkeypatch):
    response = client_with_fake_model(monkeypatch).post(
        "/predict",
        content='{"features":{"feature_a":NaN,"feature_b":4}}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert_no_inference_output(response)


@pytest.mark.parametrize(
    "payload",
    [
        {"features": {}},
        {"features": {"feature_a": 2, "feature_b": 4}, "unexpected": "extra"},
        {"features": {"feature_a": 2, "feature_b": 4, "extra_feature": 6}},
    ],
)
def test_predict_rejects_empty_or_unexpected_fields(monkeypatch, payload):
    response = client_with_fake_model(monkeypatch).post("/predict", json=payload)
    assert response.status_code == 422
    assert_no_inference_output(response)


def test_predict_accepts_numeric_strings_and_persists_normalized_floats(monkeypatch):
    response = client_with_fake_model(monkeypatch).post(
        "/predict",
        json={"features": {"feature_a": "2.5", "feature_b": "4"}},
    )
    assert response.status_code == 200
    with session() as db:
        row = db.scalar(
            select(ModelInput).where(ModelInput.exchange_id == response.headers["X-Request-ID"])
        )
        assert row.features == {"feature_a": 2.5, "feature_b": 4.0}


@pytest.mark.parametrize("route", CSV_ROUTES)
@pytest.mark.parametrize("value", ["NaN", "text"])
def test_each_csv_endpoint_validates_features_with_pydantic(monkeypatch, route, value):
    content = f"feature_a,feature_b\n{value},4\n"
    if route == "/score/file":
        content = f"feature_a,feature_b,a_quitte_l_entreprise\n{value},4,Oui\n"
    response = upload(client_with_fake_model(monkeypatch), route, content)
    assert response.status_code == 422
    errors = response.json()["detail"]["validation_errors"]
    assert "feature_a" in errors[0]["loc"]
    assert "input" not in errors[0]
    assert_no_inference_output(response)


@pytest.mark.parametrize("route", CSV_ROUTES)
def test_each_csv_endpoint_requires_a_file(monkeypatch, route):
    response = client_with_fake_model(monkeypatch).post(route)
    assert response.status_code == 422
    assert_no_inference_output(response)


@pytest.mark.parametrize("employee_id", ["0", "-1", "abc", "2147483648"])
def test_employee_endpoint_validates_id_before_lookup(monkeypatch, employee_id):
    response = client_with_fake_model(monkeypatch).get(f"/employees/{employee_id}/score")
    assert response.status_code == 422
    assert_no_inference_output(response)


@pytest.mark.parametrize(
    "route, expected",
    [
        ("/health", {"status": "ok"}),
        ("/features", {"features": ["feature_a", "feature_b"]}),
    ],
)
def test_information_endpoints_return_validated_responses(monkeypatch, route, expected):
    response = client_with_fake_model(monkeypatch).get(route)
    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize("route", ["/health", "/features"])
def test_information_endpoints_report_missing_model(monkeypatch, route):
    client = client_with_fake_model(monkeypatch)

    def unavailable():
        raise HTTPException(status_code=503, detail="Modèle indisponible.")

    monkeypatch.setattr(api, "get_model_bundle", unavailable)
    assert client.get(route).status_code == 503


@pytest.mark.parametrize(
    "probabilities",
    [
        [[True, False]],
        [[float("nan"), 0.5]],
        [[-0.1, 1.1]],
        [[0.2, 0.2]],
        [[0.2, 0.3, 0.5]],
        [],
    ],
)
def test_invalid_model_probabilities_are_neither_returned_nor_persisted(monkeypatch, probabilities):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    bundle["model"].predict_proba = lambda frame: probabilities
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = upload(client, "/predict-proba/file", "feature_a,feature_b\n2,4\n")
    assert response.status_code == 500
    assert_no_inference_output(response)
    with session() as db:
        exchange = db.get(ApiExchange, response.headers["X-Request-ID"])
        assert exchange.status == "failed"
        assert exchange.processing_stage == "model_running"


@pytest.mark.parametrize("predictions", [[0.5], [2], [1, 1]])
def test_invalid_model_predictions_are_not_silently_converted(monkeypatch, predictions):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    bundle["model"].predict = lambda frame: np.array(predictions)
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n")
    assert response.status_code == 500
    assert_no_inference_output(response)


def test_invalid_model_score_is_rejected_before_storage(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    bundle["model"].score = lambda frame, labels: 1.1
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = upload(client, "/score/file", "feature_a,feature_b,a_quitte_l_entreprise\n2,4,Oui\n")
    assert response.status_code == 500
    assert_no_inference_output(response)


def test_empty_target_parameter_is_rejected(monkeypatch):
    response = upload(
        client_with_fake_model(monkeypatch),
        "/score/file?target_column=",
        "feature_a,feature_b\n2,4\n",
    )
    assert response.status_code == 422
    assert_no_inference_output(response)
