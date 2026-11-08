"""Identifiants des outils locaux, jamais transmis en arguments de commande."""

import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS = ROOT / ".local/api-credentials.env"


def client_credentials(path: Path = DEFAULT_CREDENTIALS) -> tuple[str, str]:
    values = dotenv_values(path) if path.is_file() else {}
    username = os.environ.get("HRNOVA_VERIFY_USERNAME") or values.get("HRNOVA_VERIFY_USERNAME")
    password = os.environ.get("HRNOVA_VERIFY_PASSWORD") or values.get("HRNOVA_VERIFY_PASSWORD")
    if not username or not password:
        raise ValueError(
            "Configurer HRNOVA_VERIFY_USERNAME et HRNOVA_VERIFY_PASSWORD, "
            "ou lancer scripts/manage_users.py --bootstrap-local."
        )
    return username, password
