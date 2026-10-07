from fastapi.testclient import TestClient

import api


class FakeModel:
    classes_ = (0, 1)

    def predict_proba(self, frame):
        assert frame.columns.tolist() == ["feature_a", "feature_b"]
        return [[0.25, 0.75]]


def client_with_fake_model(monkeypatch):
    monkeypatch.setattr(
        api,
        "get_model_bundle",
        lambda: {
            "model": FakeModel(),
            "threshold": 0.6,
            "feature_names": ["feature_a", "feature_b"],
            "positive_class": 1,
            "records_by_employee_id": {
                "42": {"feature_a": 2, "feature_b": 4},
            },
        },
    )
    return TestClient(api.app)


def test_predict_returns_calibrated_probability_and_threshold(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    response = client.post(
        "/predict",
        json={"features": {"feature_b": 4, "feature_a": 2}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "probability": 0.75,
        "threshold": 0.6,
        "prediction": 1,
        "decision": "Risque de départ élevé",
    }


def test_predict_rejects_missing_features(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    response = client.post("/predict", json={"features": {"feature_a": 2}})

    assert response.status_code == 422
    assert response.json()["detail"]["missing_features"] == ["feature_b"]


def test_predict_rejects_non_finite_values(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    response = client.post(
        "/predict",
        json={"features": {"feature_a": "nan", "feature_b": 4}},
    )

    assert response.status_code == 422


def test_score_employee_looks_up_features_by_id(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    response = client.get("/employees/42/score")

    assert response.status_code == 200
    assert response.json() == {
        "employee_id": 42,
        "probability": 0.75,
        "threshold": 0.6,
        "prediction": 1,
        "decision": "Risque de départ élevé",
    }


def test_score_employee_returns_404_for_unknown_id(monkeypatch):
    client = client_with_fake_model(monkeypatch)

    response = client.get("/employees/999/score")

    assert response.status_code == 404