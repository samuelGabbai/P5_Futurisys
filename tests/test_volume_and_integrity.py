"""Frontières de volume et contraintes vérifiées dans SQLite et PostgreSQL."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

import api
from database import ApiExchange, ModelInput, session
from test_api import client_with_fake_model, upload


def test_csv_accepts_limit_but_rejects_next_row_before_inference(monkeypatch):
    monkeypatch.setattr(api, "MAX_CSV_ROWS", 2)
    client = client_with_fake_model(monkeypatch)
    accepted = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n\n6,8\n")
    assert accepted.status_code == 200
    assert accepted.json()["row_count"] == 2
    rejected = upload(client, "/predict/file", "feature_a,feature_b\n2,4\n6,8\n9,10\n")
    assert rejected.status_code == 413
    with session() as db:
        exchange = db.get(ApiExchange, rejected.headers["X-Request-ID"])
        assert exchange.status == "rejected"
        assert exchange.row_count is None


def test_csv_rejects_excessive_column_count(monkeypatch):
    monkeypatch.setattr(api, "MAX_CSV_COLUMNS", 2)
    response = upload(client_with_fake_model(monkeypatch), "/predict/file", "a,b,c\n1,2,3\n")
    assert response.status_code == 422
    assert "colonnes" in response.text


def test_orphan_model_input_cannot_be_inserted():
    with pytest.raises(IntegrityError):
        with session() as db, db.begin():
            db.add(ModelInput(exchange_id=str(uuid4()), row_index=0, features={"a": 1}))


def test_request_cannot_contain_duplicate_row_indices():
    request_id = str(uuid4())
    with session() as db, db.begin():
        db.add(ApiExchange(id=request_id, method="POST", endpoint="/predict"))
    with pytest.raises(IntegrityError):
        with session() as db, db.begin():
            db.add_all(
                [
                    ModelInput(exchange_id=request_id, row_index=0, features={"a": 1})
                    for _ in range(2)
                ]
            )
