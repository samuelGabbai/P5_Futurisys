"""Recette PostgreSQL des agrégats, des exclusions et du seuil de petits groupes."""

from pathlib import Path

import pytest
from sqlalchemy import text

from database import ApiExchange, ModelOutput, session


def test_analytics_views_count_statuses_and_mask_small_score_groups(isolated_database):
    if isolated_database.dialect.name != "postgresql":
        pytest.skip("PostgreSQL requis pour les agrégats et opérateurs JSONB")
    with session() as db, db.begin():
        for i in range(6):
            db.add(
                ApiExchange(
                    id=f"score-{i}",
                    method="POST",
                    endpoint="/predict",
                    status="succeeded",
                    http_status=200,
                    operation="threshold_predict",
                    model_sha256="test-model",
                    row_count=1,
                    duration_ms=100 + i,
                )
            )
        db.add(
            ApiExchange(
                id="rejected",
                method="POST",
                endpoint="/predict",
                status="rejected",
                http_status=403,
                duration_ms=10,
            )
        )
        db.flush()
        for i in range(6):
            db.add(
                ModelOutput(
                    exchange_id=f"score-{i}",
                    payload={"threshold": 0.6, "probability": 0.8, "prediction": 1},
                    model_values={},
                )
            )
    schema = isolated_database.get_execution_options()["schema_translate_map"][None]
    sql = (
        Path(__file__).resolve().parents[1] / "docs/migrations/003_analytics_views.sql"
    ).read_text()
    with isolated_database.begin() as conn:
        conn.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        conn.exec_driver_sql(sql)
        conn.exec_driver_sql(sql)
        row = conn.execute(text("SELECT * FROM analytics_daily_activity")).mappings().one()
        assert row["requests"] == 7
        assert row["succeeded"] == 6 and row["rejected"] == row["access_denied"] == 1
        assert row["processed_rows"] == 6 and row["p95_duration_ms"] > 100
        scores = conn.execute(text("SELECT * FROM analytics_model_scores")).mappings().one()
        assert scores["scored_requests"] == 6 and float(scores["high_risk_request_rate"]) == 1
        assert "employee_id" not in scores
        # Réduire le groupe à quatre succès : sa ligne doit disparaître de la vue métier.
        conn.execute(
            text("UPDATE api_exchanges SET status='failed' WHERE id IN ('score-0','score-1')")
        )
        assert conn.execute(text("SELECT COUNT(*) FROM analytics_model_scores")).scalar() == 0
