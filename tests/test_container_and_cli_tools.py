"""Contrôler construction, secrets, nettoyage Docker et commandes de livraison."""

from fnmatch import fnmatch
import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, Mock

import httpx
import pytest

from scripts import export_openapi, publish_huggingface, run_postgres_tests, smoke_container

ROOT = Path(__file__).resolve().parents[1]


def test_docker_context_contains_every_local_copy_and_excludes_secrets():
    patterns = (ROOT / ".dockerignore").read_text().splitlines()

    def included(path):
        result = True
        for pattern in patterns:
            negative = pattern.startswith("!")
            if fnmatch(path, pattern.lstrip("!")):
                result = negative
        return result

    sources = []
    for line in (ROOT / "Dockerfile").read_text().splitlines():
        if line.startswith("COPY ") and not line.startswith("COPY --from="):
            sources.extend(line.split()[1:-1])
    assert all((ROOT / source).exists() and included(source) for source in sources)
    assert not included(".env")
    assert not included(".local/api-credentials.env")


def configure_smoke(monkeypatch, failing_status=False, ready=True):
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test/db")
    monkeypatch.setenv("HRNOVA_AUTH_USERS", "temporary-hashes")
    monkeypatch.setattr(smoke_container, "load_dotenv", lambda *_: None)
    monkeypatch.setattr(smoke_container, "client_credentials", lambda: ("application", "secret"))
    monkeypatch.setattr(
        smoke_container,
        "dotenv_values",
        lambda _: {
            "HRNOVA_DELIVERY_USERNAME": "delivery",
            "HRNOVA_DELIVERY_PASSWORD": "delivery-secret",
        },
    )
    monkeypatch.setattr(smoke_container, "docker", lambda args, env: calls.append(args))
    client = MagicMock()

    def request(method, path, auth=None, **_):
        status = 200
        if path == "/health" and not ready:
            raise httpx.ConnectError("offline")
        if path == "/features" and auth is None:
            status = 401
        if path == "/model/download" and auth[0] == "application":
            status = 403
        if path == "/predict" and auth[0] == "delivery":
            status = 403
        if failing_status and path == "/auth/me":
            status = 500
        return httpx.Response(status, headers={"X-Request-ID": "test-id"})

    client.get.side_effect = lambda path, **kw: request("GET", path, **kw)
    client.post.side_effect = lambda path, **kw: request("POST", path, **kw)
    client.__enter__.return_value = client
    monkeypatch.setattr(smoke_container.httpx, "Client", Mock(return_value=client))
    return calls


@pytest.mark.parametrize("fail", [False, True])
def test_container_permissions_are_checked_and_container_is_always_stopped(monkeypatch, fail):
    calls = configure_smoke(monkeypatch, failing_status=fail)
    if fail:
        with pytest.raises(RuntimeError, match="permission"):
            smoke_container.smoke("image:test")
    else:
        smoke_container.smoke("image:test")
    assert calls[0][0] == "run" and calls[-1][0] == "stop"
    assert "secret" not in " ".join(calls[0])
    assert "--read-only" in calls[0]


def test_container_readiness_timeout_still_cleans_up(monkeypatch):
    calls = configure_smoke(monkeypatch, ready=False)
    times = iter([0, 61])
    monkeypatch.setattr(smoke_container, "monotonic", lambda: next(times))
    with pytest.raises(RuntimeError, match="disponible"):
        smoke_container.smoke("image:test")
    assert calls[-1][0] == "stop"


def test_docker_wrapper_never_prints_raw_command_errors(monkeypatch):
    monkeypatch.setattr(
        smoke_container.subprocess, "run", Mock(return_value=Mock(returncode=0, stdout="ok\n"))
    )
    assert smoke_container.docker(["ps"], {}) == "ok"
    monkeypatch.setattr(
        smoke_container.subprocess, "run", Mock(return_value=Mock(returncode=1, stderr="private"))
    )
    with pytest.raises(RuntimeError) as error:
        smoke_container.docker(["ps"], {})
    assert "private" not in str(error.value)


def test_exported_contract_preserves_authentication_and_binary_model_response(
    monkeypatch, tmp_path
):
    output = tmp_path / "schema.json"
    monkeypatch.setattr(sys, "argv", ["export_openapi.py", "--output", str(output)])
    export_openapi.main()
    schema = json.loads(output.read_text())
    assert schema["paths"]["/predict"]["post"]["security"]
    assert (
        "application/zip"
        in schema["paths"]["/model/download"]["get"]["responses"]["200"]["content"]
    )


def test_publication_cli_prepare_publish_and_permission_errors(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        sys, "argv", ["publish_huggingface.py", "--prepare-only", "--git-sha", "test-sha"]
    )
    monkeypatch.setattr(
        publish_huggingface,
        "prepare_release",
        lambda *_: {"model_sha256": "hash", "git_sha": "test-sha"},
    )
    publish_huggingface.main()
    monkeypatch.setattr(sys, "argv", ["publish_huggingface.py", "--git-sha", "test-sha"])
    monkeypatch.setattr(publish_huggingface, "publish_release", Mock())
    publish_huggingface.main()

    def deny(*_):
        raise PermissionError("Droit de livraison requis.")

    monkeypatch.setattr(publish_huggingface, "publish_release", deny)
    with pytest.raises(SystemExit) as error:
        publish_huggingface.main()
    assert error.value.code == 1


@pytest.mark.parametrize("exit_code", [0, 1])
def test_postgres_runner_drops_disposable_database_even_after_failed_tests(monkeypatch, exit_code):
    connection = MagicMock()
    connect = MagicMock()
    connect.return_value.__enter__.return_value = connection
    monkeypatch.setattr(run_postgres_tests.psycopg, "connect", connect)
    monkeypatch.setattr(
        run_postgres_tests, "dotenv_values", lambda _: {"ADMIN_PASSWORD": "private-test-password"}
    )
    process = Mock(return_value=Mock(returncode=exit_code))
    monkeypatch.setattr(run_postgres_tests.subprocess, "run", process)
    assert run_postgres_tests.run_tests(["-q"]) == exit_code
    queries = [str(c.args[0]) for c in connection.execute.call_args_list]
    assert "CREATE DATABASE" in queries[0] and "DROP DATABASE" in queries[-1]
    assert "private-test-password" not in str(process.call_args.args)


def test_postgres_runner_requires_local_configuration(monkeypatch):
    monkeypatch.setattr(run_postgres_tests, "dotenv_values", lambda _: {})
    with pytest.raises(ValueError):
        run_postgres_tests.run_tests([])


def test_access_control_cli_runs_on_local_api_or_container(monkeypatch):
    configure_smoke(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["smoke_container.py", "--base-url", "http://test"])
    smoke_container.main()
    monkeypatch.setattr(sys, "argv", ["smoke_container.py", "--image", "image:test"])
    smoke_container.main()
    configure_smoke(monkeypatch, failing_status=True)
    with pytest.raises(SystemExit) as error:
        smoke_container.main()
    assert error.value.code == 1
