"""Tester l’image construite avec HTTP réel et PostgreSQL (runner Linux Docker)."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic, sleep
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import dotenv_values, load_dotenv
import httpx

from scripts.client_credentials import DEFAULT_CREDENTIALS, ROOT, client_credentials


def docker(args, env):
    result = subprocess.run(["docker", *args], env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Contrôle Docker échoué ; consulter le runner sans exposer ses secrets.")
    return result.stdout.strip()


def smoke(image, port=18080):
    load_dotenv(ROOT / ".env")
    env = dict(os.environ)
    if not env.get("DATABASE_URL") or not env.get("HRNOVA_AUTH_USERS"):
        raise ValueError("DATABASE_URL et HRNOVA_AUTH_USERS requis.")
    user = client_credentials()
    secrets = dotenv_values(DEFAULT_CREDENTIALS)
    delivery = (secrets.get("HRNOVA_DELIVERY_USERNAME"), secrets.get("HRNOVA_DELIVERY_PASSWORD"))
    if not all(delivery):
        raise ValueError("Compte de livraison temporaire requis pour le contrôle.")
    name = "hrnova-smoke-" + uuid4().hex
    started = False
    try:
        docker(
            [
                "run",
                "--detach",
                "--rm",
                "--name",
                name,
                "--network",
                "host",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--env",
                "DATABASE_URL",
                "--env",
                "HRNOVA_AUTH_USERS",
                image,
                "uvicorn",
                "api:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env,
        )
        started = True
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=15) as client:
            deadline = monotonic() + 60
            while True:
                try:
                    ready = client.get("/health").status_code == 200
                except httpx.HTTPError:
                    ready = False
                if ready:
                    break
                if monotonic() >= deadline:
                    raise RuntimeError("Le conteneur ne devient pas disponible.")
                sleep(0.5)
            check_routes(client, user, delivery)
        print(
            "Image validée : PostgreSQL, prédiction, téléchargement, refus 401/403 et traces HTTP."
        )
    finally:
        if started:
            docker(["stop", name], env)


def check_routes(client, user, delivery):
    sample = json.loads((ROOT / "examples/predict.json").read_text())
    checks = [
        (client.get("/auth/me", auth=user), 200),
        (client.get("/features"), 401),
        (client.post("/predict", auth=user, json=sample), 200),
        (client.get("/model/download", auth=user), 403),
        (client.get("/model/download", auth=delivery), 200),
        (client.post("/predict", auth=delivery, json=sample), 403),
    ]
    if any(
        response.status_code != expected or not response.headers.get("X-Request-ID")
        for response, expected in checks
    ):
        raise RuntimeError("Une route ou permission du conteneur est incorrecte.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--image")
    target.add_argument("--base-url")
    args = parser.parse_args()
    try:
        if args.image:
            smoke(args.image)
        else:
            secrets = dotenv_values(DEFAULT_CREDENTIALS)
            delivery = (
                os.environ.get("HRNOVA_DELIVERY_USERNAME")
                or secrets.get("HRNOVA_DELIVERY_USERNAME"),
                os.environ.get("HRNOVA_DELIVERY_PASSWORD")
                or secrets.get("HRNOVA_DELIVERY_PASSWORD"),
            )
            if not all(delivery):
                raise ValueError("Compte de livraison requis.")
            with httpx.Client(base_url=args.base_url, timeout=30) as client:
                check_routes(client, client_credentials(), delivery)
            print("API validée : connexion, prédiction, livraison et refus 401/403.")
    except (ValueError, RuntimeError, OSError, httpx.HTTPError):
        parser.exit(1, "Validation du conteneur échouée.\n")


if __name__ == "__main__":
    main()
