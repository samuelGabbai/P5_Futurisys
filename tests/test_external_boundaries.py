"""Tester les frontières système avec des mocks, sans Docker ni publication distante."""

import sys
from unittest.mock import MagicMock, Mock

import pytest

from scripts import deploy_api, verify_database


@pytest.mark.parametrize("capture", [False, True])
def test_docker_process_passes_secrets_only_in_environment(monkeypatch, capture):
    process = Mock(return_value=Mock(returncode=0, stdout="  container-id\n"))
    monkeypatch.setattr(deploy_api.subprocess, "run", process)
    env = {"DATABASE_URL": "private-test-url"}
    args = ["docker", "ps"]
    assert deploy_api.run(args, env, capture) == ("container-id" if capture else "")
    process.assert_called_once_with(args, env=env, text=True, capture_output=True)
    assert "private-test-url" not in str(process.call_args.args)


def test_docker_process_error_does_not_expose_output(monkeypatch, capsys):
    process = Mock(return_value=Mock(returncode=1, stdout="secret-out", stderr="secret-err"))
    monkeypatch.setattr(deploy_api.subprocess, "run", process)
    with pytest.raises(RuntimeError, match="Commande Docker échouée") as error:
        deploy_api.run(["docker", "ps"], {})
    captured = capsys.readouterr()
    assert "secret" not in str(error.value) + captured.out + captured.err


@pytest.mark.parametrize("failure", [None, ValueError, RuntimeError])
def test_deployment_cli_dispatch_and_failure_exit(monkeypatch, capsys, failure):
    deploy = Mock(side_effect=failure("Controlled failure") if failure else None)
    monkeypatch.setattr(deploy_api, "deploy", deploy)
    monkeypatch.setattr(
        sys, "argv", ["deploy_api.py", "--environment", "staging", "--image", "hrnova:test"]
    )
    if failure:
        with pytest.raises(SystemExit) as error:
            deploy_api.main()
        assert error.value.code == 1
        assert "Controlled failure" in capsys.readouterr().err
    else:
        deploy_api.main()
    deploy.assert_called_once_with("staging", "hrnova:test")


def test_privilege_query_uses_current_sql_identity_and_returns_mapping(monkeypatch):
    expected = dict(
        update_dataset=False, delete_inputs=False, update_outputs=False, insert_outputs=True
    )
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.mappings.return_value.one.return_value = expected
    monkeypatch.setattr(verify_database, "get_engine", Mock(return_value=engine))
    assert verify_database.application_privileges() == expected
    connection.execute.assert_called_once()
    query = str(connection.execute.call_args.args[0])
    for table, privilege in [
        ("employees", "UPDATE"),
        ("model_inputs", "DELETE"),
        ("model_outputs", "UPDATE"),
        ("model_outputs", "INSERT"),
    ]:
        assert f"has_table_privilege(current_user, '{table}', '{privilege}')" in query
    engine.connect.return_value.__exit__.assert_called_once()
