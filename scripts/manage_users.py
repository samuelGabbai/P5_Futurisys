"""Créer/modifier un compte local, sans exposer son mot de passe dans les arguments."""

import argparse
from getpass import getpass
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import dotenv_values, set_key

from auth import PERMISSIONS, hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--role", choices=PERMISSIONS, required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,100}", args.username):
        parser.error("Nom requis : 1 à 100 caractères parmi lettres ASCII, chiffres, _ . @ - .")
    accounts = json.loads(dotenv_values(args.env_file).get("HRNOVA_AUTH_USERS") or "{}")
    if args.disable:
        if args.username not in accounts:
            parser.error("Compte inconnu.")
        accounts[args.username]["enabled"] = False
    else:
        password = getpass("Mot de passe (12 caractères minimum) : ")
        if len(password) < 12 or not password.isascii():
            parser.error("Utiliser au moins 12 caractères ASCII (compatibilité HTTP Basic).")
        if password != getpass("Confirmer le mot de passe : "):
            parser.error("Les mots de passe diffèrent.")
        accounts[args.username] = {
            "password_hash": hash_password(password),
            "role": args.role,
            "enabled": True,
        }
    args.env_file.touch(mode=0o600, exist_ok=True)
    set_key(str(args.env_file), "HRNOVA_AUTH_USERS", json.dumps(accounts))
    args.env_file.chmod(0o600)
    print("Compte enregistré. Redémarrer l’API pour appliquer la configuration.")


if __name__ == "__main__":
    main()
