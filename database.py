"""Schéma relationnel et connexion PostgreSQL de HRNova."""

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

load_dotenv()
JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


def utc_now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"
    id_employee: Mapped[int] = mapped_column(primary_key=True)
    age: Mapped[int]
    genre: Mapped[str]
    revenu_mensuel: Mapped[int]
    statut_marital: Mapped[str]
    departement: Mapped[str]
    poste: Mapped[str]
    nombre_experiences_precedentes: Mapped[int]
    nombre_heures_travailless: Mapped[int]
    annee_experience_totale: Mapped[int]
    annees_dans_l_entreprise: Mapped[int]
    annees_dans_le_poste_actuel: Mapped[int]


class Survey(Base):
    __tablename__ = "surveys"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id_employee"), primary_key=True)
    code_sondage: Mapped[str] = mapped_column(unique=True)
    a_quitte_l_entreprise: Mapped[str]
    nombre_participation_pee: Mapped[int]
    nb_formations_suivies: Mapped[int]
    nombre_employee_sous_responsabilite: Mapped[int]
    distance_domicile_travail: Mapped[int]
    niveau_education: Mapped[int]
    domaine_etude: Mapped[str]
    ayant_enfants: Mapped[str]
    frequence_deplacement: Mapped[str]
    annees_depuis_la_derniere_promotion: Mapped[int]
    annes_sous_responsable_actuel: Mapped[int]


class Evaluation(Base):
    __tablename__ = "evaluations"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id_employee"), primary_key=True)
    eval_number: Mapped[str] = mapped_column(unique=True)
    satisfaction_employee_environnement: Mapped[int]
    note_evaluation_precedente: Mapped[int]
    niveau_hierarchique_poste: Mapped[int]
    satisfaction_employee_nature_travail: Mapped[int]
    satisfaction_employee_equipe: Mapped[int]
    satisfaction_employee_equilibre_pro_perso: Mapped[int]
    note_evaluation_actuelle: Mapped[int]
    heure_supplementaires: Mapped[str]
    augementation_salaire_precedente: Mapped[str]


class ModelVersion(Base):
    __tablename__ = "model_versions"
    sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    feature_names: Mapped[list] = mapped_column(JSON_DOCUMENT)
    threshold: Mapped[float] = mapped_column(Float)
    positive_class: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PreparedEmployee(Base):
    __tablename__ = "prepared_employees"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id_employee"), primary_key=True)
    model_sha256: Mapped[str] = mapped_column(ForeignKey("model_versions.sha256"), primary_key=True)
    features: Mapped[dict] = mapped_column(JSON_DOCUMENT)


class ApiExchange(Base):
    __tablename__ = "api_exchanges"
    __table_args__ = (CheckConstraint("status IN ('pending', 'succeeded', 'rejected', 'failed')"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    method: Mapped[str] = mapped_column(String(10))
    endpoint: Mapped[str] = mapped_column(String(255), index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    http_status: Mapped[int | None]
    error_type: Mapped[str | None] = mapped_column(String(100))
    model_sha256: Mapped[str | None] = mapped_column(ForeignKey("model_versions.sha256"))
    operation: Mapped[str | None] = mapped_column(String(40))
    filename: Mapped[str | None] = mapped_column(String(255))
    duration_ms: Mapped[float | None]
    message: Mapped[str | None] = mapped_column(String(2000))
    processing_stage: Mapped[str] = mapped_column(String(40), default="received")
    row_count: Mapped[int | None]
    feature_count: Mapped[int | None]
    request_details: Mapped[dict | None] = mapped_column(JSON_DOCUMENT)
    error_details: Mapped[dict | None] = mapped_column(JSON_DOCUMENT)
    response_summary: Mapped[dict | None] = mapped_column(JSON_DOCUMENT)


class ModelInput(Base):
    __tablename__ = "model_inputs"
    __table_args__ = (UniqueConstraint("exchange_id", "row_index"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_id: Mapped[str] = mapped_column(ForeignKey("api_exchanges.id"), index=True)
    row_index: Mapped[int]
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id_employee"))
    features: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT)
    target: Mapped[int | None]


class ModelOutput(Base):
    __tablename__ = "model_outputs"
    exchange_id: Mapped[str] = mapped_column(ForeignKey("api_exchanges.id"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON_DOCUMENT)
    model_values: Mapped[dict] = mapped_column(JSON_DOCUMENT)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


@lru_cache(maxsize=1)
def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL doit désigner la base PostgreSQL locale.")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise RuntimeError("L'API requiert PostgreSQL.")
    return engine


def session():
    return Session(get_engine(), expire_on_commit=False)
