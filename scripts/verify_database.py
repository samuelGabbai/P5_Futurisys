"""Vérifier les sources complètes et le circuit API/BDD avec le rôle applicatif."""

import json
import sys
from pathlib import Path

# Exécution directe depuis la racine, même sans installation éditable du projet.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

import api
from database import (
    ApiExchange,
    Employee,
    Evaluation,
    ModelInput,
    ModelOutput,
    PreparedEmployee,
    Survey,
    get_engine,
    session,
)


def main():
    tables = [Employee, Survey, Evaluation, PreparedEmployee]
    with session() as db:
        counts = {
            model.__tablename__: db.scalar(select(func.count()).select_from(model))
            for model in tables
        }
        for model, filename in [
            (Employee, "extrait_sirh.csv"),
            (Survey, "extrait_sondage.csv"),
            (Evaluation, "extrait_eval.csv"),
        ]:
            source = pd.read_csv(ROOT / "Data" / filename, dtype=str).to_dict(orient="records")
            records = db.scalars(
                select(model).order_by(
                    model.id_employee if model is Employee else model.employee_id
                )
            ).all()
            original_id = (
                "id_employee"
                if model is Employee
                else "code_sondage" if model is Survey else "eval_number"
            )
            by_id = {str(getattr(row, original_id)): row for row in records}
            for values in source:
                stored = by_id[values[original_id]]
                assert all(str(getattr(stored, name)) == value for name, value in values.items())
            assert len(source) == len(records) == 1470
        sha = api.get_model_bundle()["model_sha256"]
        prepared = db.scalars(
            select(PreparedEmployee)
            .where(PreparedEmployee.model_sha256 == sha)
            .order_by(PreparedEmployee.employee_id)
            .limit(2)
        ).all()
        frame = pd.DataFrame(
            [row.features for row in prepared], columns=api.get_model_bundle()["feature_names"]
        )
        truth = [db.get(Survey, row.employee_id).a_quitte_l_entreprise for row in prepared]
        employee_id = prepared[0].employee_id
    report = {"dataset_counts": counts, "source_values_preserved": True, "requests": []}
    client = TestClient(api.app)
    for route in ["/predict/file", "/predict-proba/file", "/score/file"]:
        data = frame.copy()
        if route == "/score/file":
            data[api.TARGET_COLUMN] = truth
        response = client.post(
            route, files={"file": ("verification.csv", data.to_csv(index=False), "text/csv")}
        )
        verify_response(response, route, report)
    response = client.post("/predict", json={"features": frame.iloc[0].to_dict()})
    verify_response(response, "/predict", report)
    response = client.get(f"/employees/{employee_id}/score")
    verify_response(response, "/employees/{id}/score", report)
    with get_engine().connect() as connection:
        privileges = connection.execute(text("""
            SELECT has_table_privilege(current_user, 'employees', 'UPDATE') AS update_dataset,
                   has_table_privilege(current_user, 'model_inputs', 'DELETE') AS delete_inputs,
                   has_table_privilege(current_user, 'model_outputs', 'UPDATE') AS update_outputs,
                   has_table_privilege(current_user, 'model_outputs', 'INSERT') AS insert_outputs
        """)).mappings().one()
        assert not privileges["update_dataset"]
        assert not privileges["delete_inputs"]
        assert not privileges["update_outputs"]
        assert privileges["insert_outputs"]
        report["application_role_privileges"] = dict(privileges)
    report["verified_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    destination = ROOT / "docs/database_validation.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def verify_response(response, route, report):
    assert response.status_code == 200, (route, response.status_code, response.text)
    exchange_id = response.headers["X-Request-ID"]
    with session() as db:
        assert db.get(ApiExchange, exchange_id).status == "succeeded"
        assert db.get(ModelOutput, exchange_id).payload == response.json()
        assert db.get(ModelOutput, exchange_id).model_values
        count = db.scalar(
            select(func.count())
            .select_from(ModelInput)
            .where(ModelInput.exchange_id == exchange_id)
        )
        assert count == response.json().get("row_count", 1)
    report["requests"].append(
        {
            "route": route,
            "exchange_id": exchange_id,
            "input_rows": count,
            "http_status": 200,
            "output_matches_response": True,
        }
    )


if __name__ == "__main__":
    main()
