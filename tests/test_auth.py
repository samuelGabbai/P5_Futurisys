"""Vérifier les frontières de permissions avec la véritable authentification."""

import json

from fastapi.testclient import TestClient
import pytest

from api import app
from auth import current_user, hash_password
from database import ApiExchange, session

PASSWORD = "test-password-123"
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture
def secured_client(monkeypatch, authenticated_admin):
    app.dependency_overrides.pop(current_user)
    monkeypatch.setenv(
        "HRNOVA_AUTH_USERS",
        json.dumps(
            {
                role: {"password_hash": PASSWORD_HASH, "role": role}
                for role in ("utilisateur", "livreur", "lecteur", "analyste", "admin")
            }
            | {"disabled": {"password_hash": PASSWORD_HASH, "role": "admin", "enabled": False}}
        ),
    )
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "credentials", [None, ("admin", "wrong"), ("unknown", PASSWORD), ("disabled", PASSWORD)]
)
def test_invalid_credentials(secured_client, credentials):
    response = secured_client.get("/auth/me", auth=credentials)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"
    assert PASSWORD not in response.text


@pytest.mark.parametrize("role", ["lecteur", "analyste", "admin"])
def test_identity_and_audit(secured_client, role):
    response = secured_client.get("/auth/me", auth=(role, PASSWORD))
    assert response.status_code == 200
    assert response.json()["role"] == role
    assert "password_hash" not in response.text
    with session() as db:
        exchange = db.get(ApiExchange, response.headers["x-request-id"])
        assert exchange.request_details["authenticated_user"] == role
        assert PASSWORD not in json.dumps(exchange.request_details)


@pytest.mark.parametrize(
    "path", ["/predict", "/predict/file", "/predict-proba/file", "/score/file"]
)
def test_reader_cannot_predict(secured_client, path):
    assert secured_client.post(path, auth=("lecteur", PASSWORD), json={}).status_code == 403


@pytest.mark.parametrize(
    "role,expected",
    [("lecteur", 403), ("analyste", 403), ("livreur", 403), ("utilisateur", 200), ("admin", 200)],
)
def test_employee_permissions(secured_client, monkeypatch, role, expected):
    from tests.test_api import client_with_fake_model

    client_with_fake_model(monkeypatch)
    response = secured_client.get("/employees/42/score", auth=(role, PASSWORD))
    assert response.status_code == expected


@pytest.mark.parametrize("role", ["utilisateur", "analyste", "admin"])
def test_prediction_permission(secured_client, monkeypatch, role):
    from tests.test_api import client_with_fake_model

    client_with_fake_model(monkeypatch)
    response = secured_client.post(
        "/predict", auth=(role, PASSWORD), json={"features": {"feature_a": 2, "feature_b": 4}}
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "config",
    [
        "",
        "{}",
        "[]",
        "invalid",
        '{"u":{"role":"root"}}',
        '{"u":{"role":"admin","password_hash":"invalid"}}',
    ],
)
def test_invalid_configuration_fails_closed(secured_client, monkeypatch, config):
    monkeypatch.setenv("HRNOVA_AUTH_USERS", config)
    response = secured_client.get("/auth/me", auth=("admin", PASSWORD))
    assert response.status_code == 503
    assert "invalid" not in response.text


def test_every_business_route_requires_authentication(secured_client):
    schema = app.openapi()
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            assert bool(operation.get("security")) == (path != "/health")


def test_reader_can_read_features(secured_client, monkeypatch):
    import api

    monkeypatch.setattr(api, "get_model_bundle", lambda: {"feature_names": ["a"]})
    assert secured_client.get("/features", auth=("lecteur", PASSWORD)).status_code == 200


@pytest.mark.parametrize("role", ["lecteur", "analyste", "utilisateur"])
def test_api_users_cannot_download_model(secured_client, role):
    assert secured_client.get("/model/download", auth=(role, PASSWORD)).status_code == 403


@pytest.mark.parametrize(
    "path", ["/predict", "/predict/file", "/predict-proba/file", "/score/file"]
)
def test_delivery_user_cannot_use_prediction_api(secured_client, path):
    assert secured_client.post(path, auth=("livreur", PASSWORD), json={}).status_code == 403


@pytest.mark.parametrize("role", ["livreur", "admin"])
def test_download_contains_only_release_files(secured_client, monkeypatch, tmp_path, role):
    from io import BytesIO
    from zipfile import ZipFile

    import joblib
    from sklearn.dummy import DummyClassifier
    from model_release import PUBLIC_KEYS, RELEASE_FILES

    source = tmp_path / "model.joblib"
    model = DummyClassifier().fit([[1, 2], [3, 4]], [0, 1])
    joblib.dump(
        {
            "model": model,
            "threshold": 0.5,
            "feature_names": ["a", "b"],
            "positive_class": 1,
            "records_by_employee_id": {"42": "PRIVATE"},
        },
        source,
    )
    original = source.read_bytes()
    monkeypatch.setenv("HRNOVA_MODEL_PATH", str(source))
    monkeypatch.setenv("HRNOVA_MODEL_REVISION", "source-commit")
    response = secured_client.get("/model/download", auth=(role, PASSWORD))
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == RELEASE_FILES
        exported = joblib.load(BytesIO(archive.read("turnover_model.joblib")))
        assert set(exported) == PUBLIC_KEYS
        metadata = json.loads(archive.read("metadata.json"))
        assert metadata["git_sha"] == "source-commit"
        assert "PRIVATE" not in archive.read("metadata.json").decode()
    assert source.read_bytes() == original
    with session() as db:
        exchange = db.get(ApiExchange, response.headers["x-request-id"])
        assert exchange.request_details["operation"] == "model_delivery"
        assert exchange.request_details["model_sha256"] == metadata["model_sha256"]


def test_delivery_cannot_read_features(secured_client):
    assert secured_client.get("/features", auth=("livreur", PASSWORD)).status_code == 403
