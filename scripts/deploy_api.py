"""Déployer une image testée avec Docker Compose, puis vérifier l'inférence.

Les secrets sont transmis par l'environnement du processus, jamais en arguments.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENTS = {"development": "8000", "staging": "8002", "production": "8003"}
SMOKE = """import json, urllib.request
payload = open('/app/examples/predict.json', 'rb').read()
request = urllib.request.Request('http://127.0.0.1:8000/predict', data=payload, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=60) as response:
    result = json.load(response)
    assert response.headers.get('X-Request-ID'), 'Trace absente'
    assert result['prediction'] in (0, 1), 'Prédiction invalide'
print('Inférence de contrôle réussie, avec identifiant de trace.')
"""


def configuration(environment, image, source=None):
    env = dict(os.environ if source is None else source)
    if environment not in ENVIRONMENTS:
        raise ValueError("Environnement inconnu.")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/:@-]*", image):
        raise ValueError("Référence d'image invalide.")
    url = env.get("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://") or "CHANGE_ME" in url:
        raise ValueError("Définir une DATABASE_URL PostgreSQL pour la cible.")
    port = env.get("API_PORT") or ENVIRONMENTS[environment]
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("API_PORT doit être un port valide.")
    env.update(
        APP_ENV=environment,
        HRNOVA_IMAGE=image,
        API_PORT=port,
        API_BIND_HOST=env.get("API_BIND_HOST") or "127.0.0.1",
    )
    return env


def run(args, env, capture=False):
    # Capturer les erreurs évite de publier les détails SQL ou les secrets dans les logs CI.
    result = subprocess.run(args, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Commande Docker échouée ; consulter les logs sur la machine cible.")
    return result.stdout.strip() if capture else ""


def deploy(environment, image, source=None):
    env = configuration(environment, image, source)
    compose = [
        "docker",
        "compose",
        "--project-name",
        f"hrnova-{environment}",
        "--file",
        str(ROOT / "deployment/compose.yml"),
    ]
    run(["docker", "image", "inspect", image], env)
    # Avant de toucher l'instance courante : vérifier le modèle et la BDD cible.
    print(f"[{environment}] Vérification de la base et du modèle avant remplacement.", flush=True)
    run(
        compose
        + [
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "python",
            "api",
            "/app/scripts/check_deployment.py",
        ],
        env,
    )
    container = run(compose + ["ps", "--all", "--quiet", "api"], env, capture=True)
    previous = None
    if container:
        # L'ID immuable restaure la version exacte même si une étiquette a changé.
        previous = run(
            ["docker", "inspect", "--format", "{{.Image}}", container], env, capture=True
        )
    try:
        print(f"[{environment}] Démarrage de {image} et contrôle de santé.", flush=True)
        run(compose + ["up", "--detach", "--no-build", "--wait", "--wait-timeout", "120"], env)
        print(f"[{environment}] Test d’une prédiction tracée en PostgreSQL.", flush=True)
        run(compose + ["exec", "--no-TTY", "api", "python", "-c", SMOKE], env)
    except RuntimeError:
        if previous:
            print(f"[{environment}] Échec : restauration de l’image précédente.", flush=True)
            rollback_env = {**env, "HRNOVA_IMAGE": previous}
            try:
                run(
                    compose + ["up", "--detach", "--no-build", "--wait", "--wait-timeout", "120"],
                    rollback_env,
                )
            except RuntimeError:
                raise RuntimeError(
                    "Déploiement et retour arrière échoués : intervention requise."
                ) from None
            raise RuntimeError(
                "Déploiement échoué ; image précédente restaurée. Vérifier aussi la configuration."
            ) from None
        run(compose + ["stop", "api"], env)
        raise RuntimeError("Premier déploiement échoué ; instance arrêtée.") from None
    print(
        json.dumps(
            {
                "environment": environment,
                "image": image,
                "port": int(env["API_PORT"]),
                "status": "deployed",
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    try:
        deploy(args.environment, args.image)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
