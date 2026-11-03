"""Chargement réel d'artefacts temporaires et garanties en cas d'échec API."""

from unittest.mock import Mock

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

import api
import audit
import inference
from database import ApiExchange, ModelInput, ModelOutput, ModelVersion, session
from test_api import FakeModel, client_with_fake_model, upload


@pytest.fixture
def artifact_file(tmp_path, monkeypatch):
    path = tmp_path / "model.joblib"
    joblib.dump(
        {
            "model": FakeModel(),
            "feature_names": ["feature_a", "feature_b"],
            "threshold": 0.6,
            "positive_class": 1,
        },
        path,
    )
    monkeypatch.setenv("HRNOVA_MODEL_PATH", str(path))
    api._load_artifact.cache_clear()
    yield path
    api._load_artifact.cache_clear()


def test_model_file_is_hashed_cached_and_used_by_real_loader(artifact_file):
    import hashlib

    bundle = api.get_model_bundle()
    assert bundle["model_sha256"] == hashlib.sha256(artifact_file.read_bytes()).hexdigest()
    assert bundle["feature_names"] == ["feature_a", "feature_b"]
    # Après la première lecture, le cache permet de réutiliser le modèle chargé.
    artifact_file.unlink()
    assert api.get_model_bundle() is bundle
    response = TestClient(api.app).get("/features")
    assert response.status_code == 200
    assert response.json() == {"features": ["feature_a", "feature_b"]}


def test_default_model_path_is_used(monkeypatch, artifact_file):
    monkeypatch.delenv("HRNOVA_MODEL_PATH")
    monkeypatch.setattr(api, "DEFAULT_MODEL_PATH", artifact_file)
    assert api.get_model_bundle()["threshold"] == 0.6


@pytest.mark.parametrize("payload", [{}, [], {"model": "incomplete"}])
def test_incomplete_artifact_is_rejected_and_traced(artifact_file, payload):
    joblib.dump(payload, artifact_file)
    response = TestClient(api.app).get("/health")
    assert response.status_code == 500
    assert response.json()["detail"] == "Artefact de modèle invalide."
    with session() as db:
        assert db.get(ApiExchange, response.headers["X-Request-ID"]).status == "failed"
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 0


def test_missing_artifact_returns_503_without_prediction(artifact_file):
    artifact_file.unlink()
    response = TestClient(api.app).post(
        "/predict", json={"features": {"feature_a": 2, "feature_b": 4}}
    )
    assert response.status_code == 503
    assert "Modèle indisponible" in response.json()["detail"]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0


def test_unreadable_artifact_does_not_expose_local_path(monkeypatch, artifact_file):
    monkeypatch.setattr(api.joblib, "load", Mock(side_effect=OSError("private/path")))
    response = TestClient(api.app).get("/health")
    assert response.status_code == 500
    assert "private/path" not in response.text


def test_final_audit_failure_never_reports_a_success(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    monkeypatch.setattr(audit, "finish_exchange", Mock(side_effect=SQLAlchemyError("private DSN")))
    response = client.post("/predict", json={"features": {"feature_a": 2, "feature_b": 4}})
    assert response.status_code == 503
    assert response.json()["detail"] == "Enregistrement de la requête incomplet."
    assert "private DSN" not in response.text
    with session() as db:
        assert db.get(ApiExchange, response.headers["X-Request-ID"]).status == "pending"


def test_target_cannot_replace_a_model_feature(monkeypatch):
    response = upload(
        client_with_fake_model(monkeypatch),
        "/score/file?target_column=feature_a",
        "feature_a,feature_b\n2,4\n",
    )
    assert response.status_code == 422
    assert "variable du modèle" in response.json()["detail"]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 0


@pytest.mark.parametrize("change", ["missing", "feature_names", "threshold", "positive_class"])
def test_unregistered_or_inconsistent_model_never_runs(monkeypatch, change):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    predict = Mock(side_effect=AssertionError("Le modèle ne doit pas être appelé"))
    bundle["model"].predict = predict
    if change == "missing":
        bundle["model_sha256"] = "unregistered-model"
    else:
        with session() as db, db.begin():
            version = db.get(ModelVersion, "test-model")
            setattr(
                version,
                change,
                {"feature_names": ["other"], "threshold": 0.8, "positive_class": 0}[change],
            )
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n")
    assert response.status_code == 503
    predict.assert_not_called()
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 0
        assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0


@pytest.mark.parametrize("classes,positive", [([0, 2], 1), ([0, 1], 2), ([0, 1, 2], 1)])
def test_nonbinary_model_keeps_inputs_but_does_not_save_output(monkeypatch, classes, positive):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    bundle["model"].classes_ = classes
    bundle["positive_class"] = positive
    with session() as db, db.begin():
        db.get(ModelVersion, "test-model").positive_class = positive
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = upload(client, "/predict-proba/file", "feature_a,feature_b\n2,4\n")
    assert response.status_code == 500
    assert "binaire" in response.json()["detail"]
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 1
        assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0


def test_unknown_inference_operation_is_rejected():
    bundle = {"model": FakeModel(), "positive_class": 1, "threshold": 0.6}
    with pytest.raises(ValueError, match="Opération inconnue"):
        inference._calculate(
            "unknown", pd.DataFrame([{"feature_a": 2, "feature_b": 4}]), None, bundle
        )
