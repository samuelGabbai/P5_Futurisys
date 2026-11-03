import json
import sys

from dotenv import dotenv_values
import pytest

from auth import _valid_hash
from scripts import manage_users


def test_create_and_disable_account_preserves_database_configuration(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    path.write_text("DATABASE_URL=existing-value\n")
    monkeypatch.setattr(
        sys, "argv", ["manage_users.py", "admin", "--role", "admin", "--env-file", str(path)]
    )
    monkeypatch.setattr(manage_users, "getpass", lambda prompt: "password-test-123")
    manage_users.main()
    values = dotenv_values(path)
    account = json.loads(values["HRNOVA_AUTH_USERS"])["admin"]
    assert values["DATABASE_URL"] == "existing-value"
    assert _valid_hash(account["password_hash"])
    assert "password-test-123" not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    monkeypatch.setattr(
        sys,
        "argv",
        ["manage_users.py", "admin", "--role", "admin", "--env-file", str(path), "--disable"],
    )
    manage_users.main()
    assert json.loads(dotenv_values(path)["HRNOVA_AUTH_USERS"])["admin"]["enabled"] is False


@pytest.mark.parametrize("password", ["short", "non-ascii-é-password"])
def test_invalid_password_does_not_write_configuration(monkeypatch, tmp_path, password):
    path = tmp_path / ".env"
    monkeypatch.setattr(
        sys, "argv", ["manage_users.py", "u", "--role", "lecteur", "--env-file", str(path)]
    )
    monkeypatch.setattr(manage_users, "getpass", lambda prompt: password)
    with pytest.raises(SystemExit):
        manage_users.main()
    assert not path.exists()
