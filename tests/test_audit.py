from sqlalchemy import select

from database import ApiExchange, session
from test_api import client_with_fake_model, upload
import api
import audit


def exchange_for(response):
    with session() as db:
        return db.get(ApiExchange, response.headers["X-Request-ID"])


def test_success_log_explains_csv_processing(monkeypatch):
    response = upload(
        client_with_fake_model(monkeypatch),
        "/predict/file?separator=;",
        "feature_a;feature_b\n2;4\n6;8\n",
    )
    row = exchange_for(response)
    assert response.status_code == 200
    assert row.duration_ms >= 0
    assert row.row_count == 2
    assert row.feature_count == 2
    assert row.processing_stage == "completed"
    assert "2 ligne(s)" in row.message
    assert row.response_summary["prediction_counts"] == {"1": 2}
    assert row.request_details["filename"] == "employees.csv"
    assert row.request_details["uploaded_rows"] == 2
    assert row.request_details["separator"] == ";"
    assert row.request_details["file_size_bytes"] > 0
    assert row.error_details is None


def test_csv_error_keeps_filename_and_explains_missing_features(monkeypatch):
    response = upload(client_with_fake_model(monkeypatch), "/predict/file", "feature_a\n2\n")
    row = exchange_for(response)
    assert response.status_code == 422
    assert row.filename == "employees.csv"
    assert "feature_b" in row.message
    assert row.error_details["detail"]["missing_features"] == ["feature_b"]
    assert row.processing_stage == "received"
    assert row.duration_ms >= 0


def test_validation_log_excludes_body_headers_and_unknown_query_parameters(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    response = client.post(
        "/predict?token=secret-query",
        json={"password": "secret-body"},
        headers={"Authorization": "Bearer secret-header"},
    )
    row = exchange_for(response)
    assert response.status_code == 422
    assert row.error_type == "RequestValidationError"
    assert "features" in row.message
    assert row.error_details["validation_errors"]
    assert "secret-" not in str(row.error_details) + str(row.request_details)


def test_model_failure_log_identifies_stage_and_redacts_password(monkeypatch):
    client = client_with_fake_model(monkeypatch)
    bundle = api.get_model_bundle()

    def fail(frame):
        raise ValueError("model failure postgresql://user:secret-value@localhost/db")

    bundle["model"].predict = fail
    monkeypatch.setattr(api, "get_model_bundle", lambda: bundle)
    row = exchange_for(upload(client, "/predict/file", "feature_a,feature_b\n2,4\n"))
    assert row.processing_stage == "model_running"
    assert row.error_type == "ValueError"
    assert "model failure" in row.message
    assert "secret-value" not in str(row.error_details) + row.message


def test_employee_log_includes_route_template_and_id(monkeypatch):
    response = client_with_fake_model(monkeypatch).get("/employees/42/score")
    row = exchange_for(response)
    assert row.request_details["route_template"] == "/employees/{employee_id}/score"
    assert row.request_details["path_parameters"] == {"employee_id": "42"}
    assert row.response_summary["employee_id"] == 42


def test_database_errors_do_not_copy_sql_parameters_into_logs():
    from sqlalchemy.exc import StatementError

    details = audit.exception_details(
        StatementError("failure", "INSERT INTO ...", {"password": "secret"}, ValueError("bad"))
    )
    assert "secret" not in str(details)
    assert "INSERT" not in str(details)
