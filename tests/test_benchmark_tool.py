import json
from pathlib import Path
import sys
from unittest.mock import Mock

import httpx
import pytest

from scripts import benchmark_api as bench


def response(status, body):
    return httpx.Response(
        status,
        json=body,
        headers={"X-Request-ID": "test-id"},
        request=httpx.Request("POST", "http://test/predict"),
    )


def test_benchmark_counts_failures_and_reports_latency_and_throughput():
    client = Mock()
    client.post.side_effect = [
        response(200, {"row_count": 2}),
        response(200, {"row_count": 2}),
        response(403, {"detail": "forbidden"}),
        httpx.ConnectError("unavailable"),
    ]
    report = bench.measure(client, "/predict-proba/file", {}, 3, 1, 2)
    assert report["errors"] == 2
    assert report["status_counts"] == {"0": 1, "200": 1, "403": 1}
    assert report["successful_rows_per_second"] > 0
    assert report["latency_ms"]["p95"] <= report["latency_ms"]["max"]


def test_benchmark_rejects_unavailable_service_at_warmup():
    client = Mock()
    client.post.return_value = response(503, {})
    with pytest.raises(httpx.HTTPStatusError):
        bench.measure(client, "/predict", {}, 1, 1, 1)


def test_benchmark_builds_realistic_csv_cases_and_omits_credentials(monkeypatch):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)

    def post(route, **kwargs):
        size = len(kwargs["files"]["file"][1].splitlines()) - 1 if "files" in kwargs else 1
        return response(200, {"row_count": size})

    client.post.side_effect = post
    monkeypatch.setattr(bench.httpx, "Client", Mock(return_value=client))
    report = bench.run_benchmark("http://test", ("user", "private-password"), 2, (1, 2), (3,))
    assert len(report["scenarios"]) == 4
    assert {r["rows_per_request"] for r in report["scenarios"]} == {1, 3}
    assert "private-password" not in json.dumps(report)


@pytest.mark.parametrize("value", ["0", "-1", "1,a", ""])
def test_benchmark_configuration_rejects_invalid_values(value):
    with pytest.raises(Exception, match="entiers positifs"):
        bench.positive_list(value)


def test_benchmark_cli_reports_results_and_enforces_error_and_latency_budgets(
    monkeypatch, tmp_path
):
    path = tmp_path / "result.json"
    monkeypatch.setattr(
        sys, "argv", ["benchmark_api.py", "--output", str(path), "--max-p95-ms", "100"]
    )
    monkeypatch.setattr(bench, "client_credentials", lambda _: ("u", "secret"))
    report = {"scenarios": [{"errors": 0, "latency_ms": {"p95": 50}}]}
    monkeypatch.setattr(bench, "run_benchmark", lambda *_: report)
    bench.main()
    assert json.loads(path.read_text()) == report
    for errors, latency in [(1, 50), (0, 150)]:
        report["scenarios"][0].update(errors=errors, latency_ms={"p95": latency})
        with pytest.raises(SystemExit) as error:
            bench.main()
        assert error.value.code == 1
    monkeypatch.setattr(sys, "argv", ["benchmark_api.py", "--requests", "0"])
    with pytest.raises(SystemExit):
        bench.main()


def test_benchmark_accepts_positive_lists_and_hides_connection_errors(monkeypatch, capsys):
    assert bench.positive_list("1,4") == (1, 4)
    monkeypatch.setattr(sys, "argv", ["benchmark_api.py"])
    monkeypatch.setattr(bench, "client_credentials", lambda _: ("u", "password"))

    def unavailable(*_):
        raise httpx.ConnectError("private-password")

    monkeypatch.setattr(bench, "run_benchmark", unavailable)
    with pytest.raises(SystemExit) as error:
        bench.main()
    assert error.value.code == 1
    assert "private-password" not in capsys.readouterr().err
