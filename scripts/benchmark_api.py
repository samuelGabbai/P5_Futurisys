"""Mesurer une API réellement lancée, authentifiée et tracée en PostgreSQL."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
from statistics import mean
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import numpy as np
import pandas as pd

from scripts.client_credentials import DEFAULT_CREDENTIALS, ROOT, client_credentials


def measure(client, route, kwargs, requests, concurrency, rows):
    # Un appel non mesuré préchauffe le modèle, le pool BDD et la connexion HTTP.
    warmup = client.post(route, **kwargs)
    warmup.raise_for_status()

    def request_once(_):
        start = perf_counter()
        try:
            response = client.post(route, **kwargs)
            body = response.json()
            valid = response.status_code == 200 and bool(response.headers.get("X-Request-ID"))
            valid = valid and body.get("row_count", 1) == rows
            status = response.status_code
        except (httpx.HTTPError, ValueError):
            valid, status = False, 0
        return (perf_counter() - start) * 1000, valid, status

    start = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(request_once, range(requests)))
    elapsed = perf_counter() - start
    latencies = [row[0] for row in results]
    failures = sum(not row[1] for row in results)
    return {
        "route": route,
        "rows_per_request": rows,
        "requests": requests,
        "concurrency": concurrency,
        "errors": failures,
        "status_counts": {
            str(status): sum(r[2] == status for r in results)
            for status in sorted({r[2] for r in results})
        },
        "latency_ms": {
            "mean": round(mean(latencies), 2),
            "p50": round(float(np.percentile(latencies, 50)), 2),
            "p95": round(float(np.percentile(latencies, 95)), 2),
            "max": round(max(latencies), 2),
        },
        "elapsed_seconds": round(elapsed, 3),
        "requests_per_second": round(requests / elapsed, 3),
        "successful_rows_per_second": round((requests - failures) * rows / elapsed, 3),
    }


def run_benchmark(base_url, credentials, requests=8, concurrencies=(1, 4), batches=(100, 1000)):
    sample = json.loads((ROOT / "examples/predict.json").read_text())
    csv_cases = [
        (size, pd.DataFrame([sample["features"]] * size).to_csv(index=False).encode())
        for size in batches
    ]
    results = []
    with httpx.Client(base_url=base_url, auth=credentials, timeout=60) as client:
        for concurrency in concurrencies:
            results.append(measure(client, "/predict", {"json": sample}, requests, concurrency, 1))
            for size, content in csv_cases:
                results.append(
                    measure(
                        client,
                        "/predict-proba/file",
                        {"files": {"file": ("benchmark_synthetic.csv", content, "text/csv")}},
                        requests,
                        concurrency,
                        size,
                    )
                )
    return {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "HTTP réel, Basic à chaque appel, PostgreSQL et journal inclus ; préchauffage exclu",
        "machine": {
            "system": platform.system(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "python": platform.python_version(),
        },
        "data": "Profils synthétiques répétés de examples/predict.json ; aucune performance prédictive mesurée",
        "scenarios": results,
    }


def positive_list(value):
    try:
        values = tuple(int(v) for v in value.split(","))
        if not values or any(v < 1 for v in values):
            raise ValueError
        return values
    except ValueError:
        raise argparse.ArgumentTypeError("Liste d’entiers positifs attendue.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=positive_list, default=(1, 4))
    parser.add_argument("--batch-sizes", type=positive_list, default=(100, 1000))
    parser.add_argument("--output", type=Path, default=ROOT / "docs/performance_results.json")
    parser.add_argument("--max-p95-ms", type=float)
    args = parser.parse_args()
    if args.requests < 1 or max(args.batch_sizes) > 10_000:
        parser.error("Requêtes positives et lots limités à 10 000 lignes requis.")
    try:
        report = run_benchmark(
            args.base_url,
            client_credentials(args.credentials_file),
            args.requests,
            args.concurrency,
            args.batch_sizes,
        )
    except (httpx.HTTPError, ValueError):
        parser.exit(1, "Mesure impossible : contrôler le service et les identifiants.\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(s["errors"] for s in report["scenarios"]):
        parser.exit(1, "Des requêtes ont échoué ; rapport enregistré.\n")
    if args.max_p95_ms and any(
        s["latency_ms"]["p95"] > args.max_p95_ms for s in report["scenarios"]
    ):
        parser.exit(1, "Budget de latence p95 dépassé ; rapport enregistré.\n")


if __name__ == "__main__":
    main()
