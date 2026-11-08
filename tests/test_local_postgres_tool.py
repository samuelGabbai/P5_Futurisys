"""Tester l’initialisation et la sauvegarde sans lancer ni effacer de serveur réel."""

from pathlib import Path
from unittest.mock import MagicMock, Mock
import sys

import pytest

from scripts import local_postgres as pg


@pytest.fixture
def local_pg(monkeypatch, tmp_path):
    for name, path in {
        "ROOT": tmp_path,
        "LOCAL": tmp_path / ".local",
        "DATA": tmp_path / ".local/postgres",
        "ADMIN_ENV": tmp_path / ".local/admin.env",
    }.items():
        monkeypatch.setattr(pg, name, path)
    calls = []

    def run(*args, **kwargs):
        calls.append((args, kwargs))
        if Path(args[0]).name == "initdb":
            pg.DATA.mkdir(parents=True)

    monkeypatch.setattr(pg, "run", run)
    monkeypatch.setattr(pg.subprocess, "run", Mock(return_value=Mock(returncode=1)))
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = None
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(pg.psycopg, "connect", connect)
    monkeypatch.setattr(sys, "argv", ["local_postgres.py", "start", "--pg-bin", "/fake/pg"])
    return calls, connection


def test_first_start_uses_scram_private_credentials_and_limited_role(local_pg):
    calls, connection = local_pg
    pg.main()
    assert "--auth-host=scram-sha-256" in calls[0][0]
    assert pg.ADMIN_ENV.stat().st_mode & 0o777 == 0o600
    assert (pg.ROOT / ".env").stat().st_mode & 0o777 == 0o600
    assert not (pg.LOCAL / "init-password").exists()
    queries = [str(c.args[0]) for c in connection.execute.call_args_list]
    assert any("NOSUPERUSER NOCREATEDB NOCREATEROLE" in q for q in queries)
    assert any("GRANT SELECT" in q for q in queries)
    assert any("GRANT INSERT" in q for q in queries)
    assert "listen_addresses = '127.0.0.1'" in (pg.DATA / "postgresql.conf").read_text()


def test_start_preserves_existing_env_and_recreate_backs_up_before_drop(local_pg, monkeypatch):
    calls, connection = local_pg
    pg.LOCAL.mkdir()
    pg.ADMIN_ENV.write_text("ADMIN_PASSWORD=test-admin\nAPP_PASSWORD=test-app\n")
    pg.DATA.mkdir()
    (pg.DATA / "PG_VERSION").write_text("18")
    existing = "DATABASE_URL=keep-existing\nHRNOVA_AUTH_USERS=keep-accounts\n"
    (pg.ROOT / ".env").write_text(existing)
    connection.execute.return_value.fetchone.return_value = (1,)

    def run(*args, **kwargs):
        calls.append((args, kwargs))
        if Path(args[0]).name == "pg_dump":
            Path(args[-1]).write_bytes(b"backup")

    monkeypatch.setattr(pg, "run", run)
    monkeypatch.setattr(sys, "argv", ["local_postgres.py", "recreate", "--pg-bin", "/fake/pg"])
    pg.main()
    assert (pg.ROOT / ".env").read_text() == existing
    assert len(list((pg.LOCAL / "backups").glob("*.dump"))) == 1
    assert any(Path(args[0]).name == "pg_dump" for args, _ in calls)
    assert any("DROP DATABASE hrnova" in str(c.args[0]) for c in connection.execute.call_args_list)


def test_existing_configuration_is_not_reinitialized(local_pg):
    (pg.ROOT / ".env").write_text("existing")
    with pytest.raises(SystemExit, match="existante"):
        pg.main()


@pytest.mark.parametrize("action", ["status", "stop"])
def test_status_and_stop_do_not_initialize_anything(local_pg, monkeypatch, action):
    calls, _ = local_pg
    monkeypatch.setattr(sys, "argv", ["local_postgres.py", action, "--pg-bin", "/fake/pg"])
    pg.main()
    assert calls[0][0][-1] == action
    assert not pg.LOCAL.exists()


def test_command_wrapper_converts_paths_and_checks_exit_status(monkeypatch):
    run = Mock()
    monkeypatch.setattr(pg.subprocess, "run", run)
    # Récupérer la vraie fonction, non remplacée par la fixture local_pg.
    pg.run(Path("/fake/pg_ctl"), "status")
    assert run.call_args.args[0] == ["/fake/pg_ctl", "status"]
    assert run.call_args.kwargs["check"] is True
