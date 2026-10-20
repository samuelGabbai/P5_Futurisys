from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import SQLAlchemyError

import api
import database
from create_db import import_dataset
from database import (
    ApiExchange,
    Employee,
    Evaluation,
    ModelInput,
    ModelOutput,
    PreparedEmployee,
    Survey,
    session,
)
from test_api import FakeModel, client_with_fake_model, upload


def test_model_reads_committed_inputs_and_response_is_persisted(monkeypatch):
    class CheckingModel(FakeModel):
        def predict(self, frame):
            # Une session distincte voit les entrées avant tout calcul.
            with session() as db:
                stored = db.scalars(select(ModelInput).order_by(ModelInput.row_index)).all()
                assert len(stored) == 2
                assert [row.features for row in stored] == frame.to_dict(orient="records")
                assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0
            return super().predict(frame)

    client = client_with_fake_model(monkeypatch)
    original = api.get_model_bundle()
    original["model"] = CheckingModel()
    monkeypatch.setattr(api, "get_model_bundle", lambda: original)
    response = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n6,8\n")
    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    with session() as db:
        exchange = db.get(ApiExchange, request_id)
        assert exchange.status == "succeeded"
        assert exchange.http_status == 200
        assert exchange.model_sha256 == "test-model"
        assert exchange.filename == "employees.csv"
        assert exchange.operation == "predict"
        assert exchange.completed_at is not None
        assert db.get(ModelOutput, request_id).payload == response.json()


def test_rejected_csv_is_traced_without_inference(monkeypatch):
    response = upload(client_with_fake_model(monkeypatch), "/predict/file", "feature_a\n2\n")
    assert response.status_code == 422
    with session() as db:
        exchange = db.get(ApiExchange, response.headers["X-Request-ID"])
        assert exchange.status == "rejected"
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 0
        assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0


def test_unavailable_database_prevents_model_execution(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    def unavailable():
        raise SQLAlchemyError("offline")

    monkeypatch.setattr(database, "get_engine", unavailable)
    response = client.post("/predict", json={"features": {"feature_a": 2, "feature_b": 4}})
    assert response.status_code == 503
    assert "X-Request-ID" in response.headers


def test_failed_model_keeps_inputs_and_failure_trace(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()

    def fail(frame):
        raise ValueError("model failure")

    bundle["model"].predict = fail
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n")
    assert response.status_code == 500
    with session() as db:
        exchange = db.get(ApiExchange, response.headers["X-Request-ID"])
        assert exchange.status == "failed"
        assert exchange.error_type == "ValueError"
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 1
        assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0


def test_failed_output_commit_never_returns_prediction(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    def reject_output(*args):
        raise SQLAlchemyError("output unavailable")

    event.listen(ModelOutput, "before_insert", reject_output)
    try:
        response = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n")
    finally:
        event.remove(ModelOutput, "before_insert", reject_output)
    assert response.status_code == 503
    with session() as db:
        assert db.get(ApiExchange, response.headers["X-Request-ID"]).status == "failed"
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 1
        assert db.scalar(select(func.count()).select_from(ModelOutput)) == 0


def test_employee_route_reads_prepared_features_from_database(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    bundle["records_by_employee_id"] = {}
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    response = client.get("/employees/42/score")
    assert response.status_code == 200
    with session() as db:
        row = db.scalar(
            select(ModelInput).where(ModelInput.exchange_id == response.headers["X-Request-ID"])
        )
        assert row.employee_id == 42
        assert row.features == {"feature_a": 2, "feature_b": 4}
        assert db.get(ModelOutput, response.headers["X-Request-ID"]).payload == response.json()


def test_failed_input_commit_prevents_calculation(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()
    called = []
    bundle["model"].predict = lambda frame: called.append(True)
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)

    def reject_input(*args):
        raise SQLAlchemyError("input unavailable")

    event.listen(ModelInput, "before_insert", reject_input)
    try:
        response = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n")
    finally:
        event.remove(ModelInput, "before_insert", reject_input)
    assert response.status_code == 503
    assert called == []
    with session() as db:
        assert db.scalar(select(func.count()).select_from(ModelInput)) == 0
        assert db.get(ApiExchange, response.headers["X-Request-ID"]).status == "failed"


def test_import_complete_dataset_is_idempotent_and_preserves_identifiers(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    # create_db importe get_engine séparément ; import_dataset utilise session(), isolée par fixture.
    first = import_dataset(root / "Data", root / "artifacts/turnover_model.joblib")
    second = import_dataset(root / "Data", root / "artifacts/turnover_model.joblib")
    assert first == second
    assert first["employees"] == 1470
    assert first["surveys"] == first["evaluations"] == 1470
    assert first["prepared_employees"] == 1471  # version factice du salarié 42 conservée
    with session() as db:
        assert db.get(Survey, 1).code_sondage == "000001"
        assert db.get(Evaluation, 1).eval_number == "E_1"
        assert db.get(Employee, 1).age == 41
