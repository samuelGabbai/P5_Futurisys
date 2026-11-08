"""Créer/modifier un compte local, sans exposer son mot de passe dans les arguments."""

import argparse
from getpass import getpass
import json
import re
import secrets
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import dotenv_values, set_key

from auth import PERMISSIONS, hash_password


def bootstrap_local(env_file: Path, credentials_file: Path) -> bool:
    """Initialiser les comptes locaux une fois, sans réinitialiser un compte existant."""
    existing = dotenv_values(env_file).get("HRNOVA_AUTH_USERS")
    if existing and json.loads(existing):
        return False
    if credentials_file.exists():
        raise ValueError(
            "Identifiants locaux déjà présents : conserver ou réconcilier la configuration."
        )
    passwords = {name: secrets.token_urlsafe(24) for name in ("application", "livraison", "admin")}
    accounts = {
        name: {"password_hash": hash_password(passwords[name]), "role": role, "enabled": True}
        for name, role in (
            ("application", "utilisateur"),
            ("livraison", "livreur"),
            ("admin", "admin"),
        )
    }
    credentials_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with credentials_file.open("x") as stream:
        credentials_file.chmod(0o600)
        for prefix, name in (
            ("VERIFY", "application"),
            ("SMOKE", "application"),
            ("DELIVERY", "livraison"),
            ("ADMIN", "admin"),
        ):
            stream.write(
                f"HRNOVA_{prefix}_USERNAME={name}\nHRNOVA_{prefix}_PASSWORD={passwords[name]}\n"
            )
    env_file.touch(mode=0o600, exist_ok=True)
    set_key(str(env_file), "HRNOVA_AUTH_USERS", json.dumps(accounts))
    env_file.chmod(0o600)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", nargs="?")
    parser.add_argument("--role", choices=PERMISSIONS)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--bootstrap-local", action="store_true")
    parser.add_argument("--credentials-file", type=Path, default=Path(".local/api-credentials.env"))
    args = parser.parse_args()
    if args.bootstrap_local:
        if args.username or args.role or args.disable:
            parser.error("--bootstrap-local s’utilise sans nom, rôle ou désactivation.")
        created = bootstrap_local(args.env_file, args.credentials_file)
        print(
            "Comptes locaux créés ; identifiants dans " + str(args.credentials_file)
            if created
            else "Comptes existants conservés, aucun mot de passe modifié."
        )
        return
    if not args.username or not args.role:
        parser.error("Indiquer un nom et --role, ou --bootstrap-local.")
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
