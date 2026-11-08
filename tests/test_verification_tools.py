"""Vérifier le parcours complet sans neutraliser les contrôles d’authentification."""

import json
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
import pytest

import api
from auth import authenticate, current_user
from create_db import import_dataset
from scripts import client_credentials, manage_users, verify_database

ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_is_private_preserves_database_and_is_idempotent(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    credentials = tmp_path / "private/accounts.env"
    env.write_text("DATABASE_URL=unchanged\n")
    assert manage_users.bootstrap_local(env, credentials) is True
    values = dotenv_values(env)
    assert values["DATABASE_URL"] == "unchanged"
    accounts = json.loads(values["HRNOVA_AUTH_USERS"])
    assert {a["role"] for a in accounts.values()} == {"utilisateur", "livreur", "admin"}
    assert credentials.stat().st_mode & 0o777 == 0o600
    assert env.stat().st_mode & 0o777 == 0o600
    original = credentials.read_bytes(), env.read_bytes()
    assert manage_users.bootstrap_local(env, credentials) is False
    assert (credentials.read_bytes(), env.read_bytes()) == original
    monkeypatch.setenv("HRNOVA_AUTH_USERS", values["HRNOVA_AUTH_USERS"])
    secret = dotenv_values(credentials)
    user = authenticate(secret["HRNOVA_VERIFY_USERNAME"], secret["HRNOVA_VERIFY_PASSWORD"])
    assert user.role == "utilisateur"
    assert "model:deliver" not in user.permissions
    assert secret["HRNOVA_VERIFY_PASSWORD"] not in env.read_text()


def test_bootstrap_never_overwrites_orphan_credentials(tmp_path):
    secret = tmp_path / "credentials.env"
    secret.write_text("existing")
    with pytest.raises(ValueError):
        manage_users.bootstrap_local(tmp_path / ".env", secret)
    assert secret.read_text() == "existing"


def test_credentials_prefer_environment_and_reject_missing_values(tmp_path, monkeypatch):
    path = tmp_path / "credentials.env"
    path.write_text("HRNOVA_VERIFY_USERNAME=file-user\nHRNOVA_VERIFY_PASSWORD=file-password\n")
    monkeypatch.delenv("HRNOVA_VERIFY_USERNAME", raising=False)
    monkeypatch.delenv("HRNOVA_VERIFY_PASSWORD", raising=False)
    assert client_credentials.client_credentials(path) == ("file-user", "file-password")
    monkeypatch.setenv("HRNOVA_VERIFY_PASSWORD", "environment-password")
    assert client_credentials.client_credentials(path)[1] == "environment-password"
    with pytest.raises(ValueError, match="Configurer"):
        client_credentials.client_credentials(tmp_path / "absent")


def test_database_verifier_authenticates_every_route(
    tmp_path, monkeypatch, isolated_database, authenticated_admin
):
    env = tmp_path / ".env"
    credentials = tmp_path / "credentials.env"
    manage_users.bootstrap_local(env, credentials)
    monkeypatch.setenv("HRNOVA_AUTH_USERS", dotenv_values(env)["HRNOVA_AUTH_USERS"])
    api.app.dependency_overrides.pop(current_user)
    import_dataset(ROOT / "Data", ROOT / "artifacts/turnover_model.joblib")
    # L’identité SQL de la fixture de tests n’est pas le rôle applicatif de production.
    # Ses droits effectifs sont vérifiés séparément par l’outil sur la vraie instance locale.
    monkeypatch.setattr(
        verify_database,
        "application_privileges",
        lambda: {
            "update_dataset": False,
            "delete_inputs": False,
            "update_outputs": False,
            "insert_outputs": True,
        },
    )
    report = verify_database.verify_database(*client_credentials.client_credentials(credentials))
    assert report["authenticated_role"] == "utilisateur"
    assert report["source_values_preserved"]
    assert len(report["requests"]) == 5
    assert all(r["http_status"] == 200 for r in report["requests"])
    assert "PASSWORD" not in json.dumps(report)
    secret = dotenv_values(credentials)
    with pytest.raises(ValueError, match="utilisateur ou admin"):
        verify_database.verify_database(
            secret["HRNOVA_DELIVERY_USERNAME"], secret["HRNOVA_DELIVERY_PASSWORD"]
        )


def test_verification_cli_writes_report_and_hides_failures(monkeypatch, tmp_path, capsys):
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["verify_database.py", "--output", str(output)])
    monkeypatch.setattr(verify_database, "client_credentials", lambda _: ("user", "secret"))
    monkeypatch.setattr(verify_database, "verify_database", lambda *_: {"verified": True})
    verify_database.main()
    assert json.loads(output.read_text()) == {"verified": True}

    def failure(*_):
        raise RuntimeError("secret must never appear")

    monkeypatch.setattr(verify_database, "verify_database", failure)
    with pytest.raises(SystemExit):
        verify_database.main()
    assert "secret must never appear" not in capsys.readouterr().err


def test_bootstrap_cli_and_invalid_manage_user_arguments(monkeypatch, tmp_path):
    env, secret = tmp_path / ".env", tmp_path / "credentials.env"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "manage_users.py",
            "--bootstrap-local",
            "--env-file",
            str(env),
            "--credentials-file",
            str(secret),
        ],
    )
    manage_users.main()
    manage_users.main()
    for args in [
        [],
        ["bad:name", "--role", "admin"],
        ["name", "--bootstrap-local"],
        ["unknown", "--role", "admin", "--disable"],
    ]:
        monkeypatch.setattr(sys, "argv", ["manage_users.py", *args, "--env-file", str(env)])
        with pytest.raises(SystemExit):
            manage_users.main()
