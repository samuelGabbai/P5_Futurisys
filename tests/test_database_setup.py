"""Création de base, CLI et rejets transactionnels sans toucher la BDD locale."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import joblib
import pandas as pd
import pytest
from sqlalchemy import event, func, select
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import SQLAlchemyError

import create_db
import database
from database import Employee, Evaluation, ModelVersion, session

# Conserver la vraie fonction avant le remplacement par la fixture BDD isolée.
ENGINE_FACTORY = create_db.get_engine
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine_factory():
    ENGINE_FACTORY.cache_clear()
    yield ENGINE_FACTORY
    ENGINE_FACTORY.cache_clear()


def test_missing_database_url_is_explicit(monkeypatch, engine_factory):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        engine_factory()


def test_nonpostgres_database_is_disposed_and_rejected(monkeypatch, engine_factory):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    engine = Mock()
    engine.dialect.name = "sqlite"
    monkeypatch.setattr(database, "create_engine", Mock(return_value=engine))
    with pytest.raises(RuntimeError, match="requiert PostgreSQL"):
        engine_factory()
    engine.dispose.assert_called_once()


def test_postgres_engine_is_cached_and_checks_connections(monkeypatch, engine_factory):
    url = "postgresql+psycopg://app:test@localhost/hrnova_test"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = Mock()
    engine.dialect.name = "postgresql"
    factory = Mock(return_value=engine)
    monkeypatch.setattr(database, "create_engine", factory)
    assert engine_factory() is engine_factory() is engine
    factory.assert_called_once_with(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    engine.dispose.assert_not_called()


@pytest.mark.parametrize("name", ["", "unsafe-name", "name;DROP", "123name"])
def test_invalid_database_name_never_opens_admin_connection(monkeypatch, name):
    monkeypatch.setenv("DATABASE_URL", f"postgresql+psycopg://app:test@localhost/{name}")
    factory = Mock()
    monkeypatch.setattr(create_db, "create_engine", factory)
    with pytest.raises(ValueError, match="Nom de base invalide"):
        create_db.create_database()
    factory.assert_not_called()


@pytest.mark.parametrize("exists", [False, True])
@pytest.mark.parametrize("explicit_admin", [False, True])
def test_database_creation_is_idempotent_and_uses_autocommit(monkeypatch, exists, explicit_admin):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:test@localhost/Demo_Test")
    monkeypatch.delenv("DATABASE_ADMIN_URL", raising=False)
    admin_url = "postgresql+psycopg://admin:secret@localhost/postgres"
    if explicit_admin:
        monkeypatch.setenv("DATABASE_ADMIN_URL", admin_url)
    engine = MagicMock()
    engine.dialect = dialect()
    conn = engine.connect.return_value.__enter__.return_value
    conn.dialect = dialect()
    conn.execute.return_value.scalar.return_value = exists
    factory = Mock(return_value=engine)
    monkeypatch.setattr(create_db, "create_engine", factory)
    create_db.create_database()
    used_url = factory.call_args.args[0]
    assert factory.call_args.kwargs == {"isolation_level": "AUTOCOMMIT"}
    if explicit_admin:
        assert used_url == admin_url
    else:
        assert used_url.database == "postgres" and used_url.username == "app"
    calls = conn.execute.call_args_list
    assert calls[0].args[1] == {"name": "Demo_Test"}
    assert "WHERE datname = :name" in str(calls[0].args[0])
    assert len(calls) == (1 if exists else 2)
    if not exists:
        assert str(calls[1].args[0]) == 'CREATE DATABASE "Demo_Test"'
    engine.dispose.assert_called_once()


def test_failed_database_creation_releases_admin_connection(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://app:test@localhost/demo")
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.side_effect = SQLAlchemyError(
        "denied"
    )
    monkeypatch.setattr(create_db, "create_engine", Mock(return_value=engine))
    with pytest.raises(SQLAlchemyError):
        create_db.create_database()
    engine.dispose.assert_called_once()


@pytest.fixture
def import_files(tmp_path):
    for filename in ("extrait_sirh.csv", "extrait_sondage.csv", "extrait_eval.csv"):
        frame = pd.read_csv(ROOT / "Data" / filename, dtype=str).head(1)
        frame.to_csv(tmp_path / filename, index=False)
    bundle = {
        "feature_names": ["feature_a", "feature_b"],
        "threshold": 0.6,
        "positive_class": 1,
        "records_by_employee_id": {"1": {"feature_a": 2, "feature_b": 4}},
    }
    model = tmp_path / "model.joblib"
    joblib.dump(bundle, model)
    return tmp_path, model, bundle


def assert_no_partial_import():
    with session() as db:
        assert db.get(Employee, 1) is None
        assert db.scalar(select(func.count()).select_from(Employee)) == 1
        assert db.scalar(select(func.count()).select_from(ModelVersion)) == 1


@pytest.mark.parametrize("defect", ["duplicate", "unmatched", "missing"])
def test_inconsistent_sources_are_rejected_before_any_write(import_files, defect):
    folder, model, _ = import_files
    path = folder / "extrait_sondage.csv"
    frame = pd.read_csv(path, dtype=str)
    if defect == "duplicate":
        frame = pd.concat([frame, frame])
    elif defect == "unmatched":
        frame["code_sondage"] = "000002"
    else:
        frame[frame.columns[-1]] = None
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        create_db.import_dataset(folder, model)
    assert_no_partial_import()


@pytest.mark.parametrize(
    "defect", ["missing_employee", "missing_feature", "extra_feature", "nonfinite"]
)
def test_invalid_prepared_model_data_never_partially_imports(import_files, defect):
    folder, model, bundle = import_files
    values = bundle["records_by_employee_id"]["1"]
    if defect == "missing_employee":
        bundle["records_by_employee_id"] = {}
    elif defect == "missing_feature":
        values.pop("feature_a")
    elif defect == "extra_feature":
        values["extra"] = 3
    else:
        values["feature_a"] = float("nan")
    joblib.dump(bundle, model)
    with pytest.raises(ValueError):
        create_db.import_dataset(folder, model)
    assert_no_partial_import()


def test_database_error_rolls_back_already_flushed_employees(import_files):
    folder, model, _ = import_files

    def fail(*args):
        raise SQLAlchemyError("evaluation unavailable")

    event.listen(Evaluation, "before_insert", fail)
    try:
        with pytest.raises(SQLAlchemyError):
            create_db.import_dataset(folder, model)
    finally:
        event.remove(Evaluation, "before_insert", fail)
    assert_no_partial_import()


@pytest.mark.parametrize("create", [False, True])
def test_creation_cli_applies_migration_and_imports_requested_files(
    monkeypatch, import_files, capsys, create
):
    folder, model, _ = import_files
    args = ["create_db.py", "--data-dir", str(folder), "--model-path", str(model)]
    if create:
        args.append("--create-database")
    monkeypatch.setattr("sys.argv", args)
    engine = MagicMock()
    monkeypatch.setattr(create_db, "get_engine", lambda: engine)
    ddl = Mock()
    monkeypatch.setattr(create_db.Base.metadata, "create_all", ddl)
    create_database = Mock()
    monkeypatch.setattr(create_db, "create_database", create_database)
    create_db.main()
    assert create_database.call_count == int(create)
    ddl.assert_called_once_with(engine)
    migrations = engine.begin.return_value.__enter__.return_value.exec_driver_sql.call_args_list
    assert "CREATE OR REPLACE VIEW api_logs" in migrations[0].args[0]
    assert "CREATE OR REPLACE VIEW analytics_daily_activity" in migrations[1].args[0]
    result = json.loads(capsys.readouterr().out)
    assert result["employees"] == 2  # employé importé + employé 42 de la fixture
    assert result["surveys"] == result["evaluations"] == 1
    with session() as db:
        assert db.get(Employee, 1) is not None


def test_postgresql_can_create_a_disposable_database_idempotently(monkeypatch):
    """En CI PostgreSQL : créer et supprimer seulement une base à nom aléatoire."""
    import os
    from uuid import uuid4

    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL requis pour l'intégration PostgreSQL")
    name = "hrnova_creation_test_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    monkeypatch.setenv(
        "DATABASE_URL", make_url(url).set(database=name).render_as_string(hide_password=False)
    )
    monkeypatch.setenv("DATABASE_ADMIN_URL", url)
    try:
        create_db.create_database()
        create_db.create_database()
        with admin.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT datname FROM pg_database WHERE datname = :name"), {"name": name}
                ).scalar_one()
                == name
            )
    finally:
        with admin.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}"')
        admin.dispose()


def test_postgresql_migration_is_repeatable_and_api_logs_view_matches_requests(
    monkeypatch, isolated_database
):
    from sqlalchemy import text
    from test_api import client_with_fake_model

    engine = isolated_database
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL requis pour la migration et la vue JSONB")
    response = client_with_fake_model(monkeypatch).get("/health")
    assert response.status_code == 200
    schema = engine.get_execution_options()["schema_translate_map"][None]
    sql = (ROOT / "docs/migrations/002_explicit_api_logs.sql").read_text()
    with engine.begin() as conn:
        # Le SQL brut utilise le search_path de ce schéma temporaire uniquement.
        conn.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        conn.exec_driver_sql(sql)
        conn.exec_driver_sql(sql)
        row = conn.execute(text("SELECT requete_id, route, code_http FROM api_logs")).one()
        assert row.requete_id == response.headers["X-Request-ID"]
        assert row.route == "/health" and row.code_http == 200
