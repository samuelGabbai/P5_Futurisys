from fastapi.testclient import TestClient
import numpy as np
import pytest

import api


class FakeModel:
    classes_ = (0, 1)

    def predict_proba(self, frame):
        assert frame.columns.tolist() == ["feature_a", "feature_b"]
        return [[0.25, 0.75] for _ in range(len(frame))]

    def predict(self, frame):
        assert frame.columns.tolist() == ["feature_a", "feature_b"]
        return np.ones(len(frame), dtype=int)

    def score(self, frame, labels):
        return float(np.mean(self.predict(frame) == labels))


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


def upload(client, route, content, filename="employees.csv"):
    return client.post(route, files={"file": (filename, content, "text/csv")})


def test_csv_predictions_preserve_rows_and_reorder_columns(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    response = upload(client, "/predict/file", "feature_b,feature_a\n4,2\n8,6\n")
    assert response.status_code == 200
    assert response.json() == {"row_count": 2, "predictions": [1, 1]}


def test_csv_probabilities_include_class_order_and_support_semicolon(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    response = upload(client, "/predict-proba/file?separator=;", "\ufefffeature_a;feature_b\n2;4\n6;8\n")
    assert response.status_code == 200
    assert response.json() == {
        "row_count": 2,
        "classes": [0, 1],
        "probabilities": [[0.25, 0.75], [0.25, 0.75]],
    }


@pytest.mark.parametrize("labels", ["0\n1", "Non\nOui"])
def test_csv_score_requires_truth_and_returns_accuracy(monkeypatch, labels):
    client = client_with_fake_model(monkeypatch)
    first, second = labels.splitlines()
    response = upload(client, "/score/file", f"feature_a,feature_b,a_quitte_l_entreprise\n2,4,{first}\n6,8,{second}\n")
    assert response.status_code == 200
    assert response.json() == {
        "row_count": 2,
        "score": 0.5,
        "metric": "accuracy",
        "threshold": 0.6,
        "threshold_accuracy": 0.5,
        "threshold_precision": 0.5,
        "threshold_recall": 1.0,
        "threshold_f1": pytest.approx(2 / 3),
    }


def test_csv_score_distinguishes_native_predictions_from_optimized_threshold(monkeypatch):
    class LowProbabilityModel(FakeModel):
        def predict_proba(self, frame):
            return [[0.45, 0.55] for _ in range(len(frame))]

    monkeypatch.setattr(api, "get_model_bundle", lambda: {
        "model": LowProbabilityModel(), "threshold": 0.6,
        "feature_names": ["feature_a", "feature_b"], "positive_class": 1,
    })
    client = TestClient(api.app)
    response = upload(client, "/score/file?target_column=target", "feature_a,feature_b,target\n2,4,1\n")
    assert response.status_code == 200
    assert response.json()["score"] == 1.0
    assert response.json()["threshold_accuracy"] == 0.0


@pytest.mark.parametrize("content", [
    "", "feature_a,feature_b\n", "feature_a,feature_a\n2,4\n",
    "feature_a,feature_b\n2,4,6\n", "feature_a,feature_b\n2\n",
    "feature_a\n2\n", "feature_a,feature_b,extra\n2,4,6\n",
    "feature_a,feature_b\ntext,4\n", "feature_a,feature_b\nnan,4\n",
    "feature_a,feature_b\ninf,4\n", "feature_a,feature_b\n,4\n",
    b"feature_a,feature_b\n\xff,4\n",
])
def test_csv_rejects_invalid_input(monkeypatch, content):
    response = upload(client_with_fake_model(monkeypatch), "/predict/file", content)
    assert response.status_code == 422


def test_csv_score_rejects_missing_or_invalid_target(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    for content in ["feature_a,feature_b\n2,4\n", "feature_a,feature_b,a_quitte_l_entreprise\n2,4,unknown\n"]:
        assert upload(client, "/score/file", content).status_code == 422


def test_csv_rejects_wrong_extension_and_large_file(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    assert upload(client, "/predict/file", "feature_a,feature_b\n2,4\n", "file.xlsx").status_code == 422
    monkeypatch.setattr(api, "MAX_CSV_BYTES", 10)
    assert upload(client, "/predict/file", "feature_a,feature_b\n2,4\n").status_code == 413
