"""BDD isolée par test : PostgreSQL en CI, SQLite pour les tests unitaires rapides."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.pool import StaticPool

import database
from database import Base, Employee, ModelVersion, PreparedEmployee, session


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        root_engine = create_engine(url)
        schema = "hrnova_test_" + uuid4().hex
        with root_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        engine = root_engine.execution_options(schema_translate_map={None: schema})
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    monkeypatch.setattr(database, "get_engine", lambda: engine)
    Base.metadata.create_all(engine)
    with session() as db, db.begin():
        db.add(
            Employee(
                id_employee=42,
                age=30,
                genre="M",
                revenu_mensuel=3000,
                statut_marital="Célibataire",
                departement="Consulting",
                poste="Consultant",
                nombre_experiences_precedentes=2,
                nombre_heures_travailless=80,
                annee_experience_totale=8,
                annees_dans_l_entreprise=4,
                annees_dans_le_poste_actuel=2,
            )
        )
        db.add(
            ModelVersion(
                sha256="test-model",
                feature_names=["feature_a", "feature_b"],
                threshold=0.6,
                positive_class=1,
            )
        )
        db.flush()
        db.add(
            PreparedEmployee(
                employee_id=42, model_sha256="test-model", features={"feature_a": 2, "feature_b": 4}
            )
        )
    yield engine
    if url:
        with root_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        root_engine.dispose()
    else:
        engine.dispose()
