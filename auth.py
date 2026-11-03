"""Authentification HTTP Basic et permissions, sans mot de passe en clair stocké."""

import hashlib
import hmac
import json
import os
import secrets
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ITERATIONS = 600_000
Role = Literal["utilisateur", "livreur", "lecteur", "analyste", "admin"]
API_PERMISSIONS = {"features:read", "predictions:write", "employees:read"}
PERMISSIONS = {
    "utilisateur": API_PERMISSIONS,
    "livreur": {"model:deliver"},
    "lecteur": {"features:read"},
    "analyste": {"features:read", "predictions:write"},
    "admin": API_PERMISSIONS | {"model:deliver"},
}
security = HTTPBasic(auto_error=False)


class Account(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password_hash: str
    role: Role
    enabled: bool = True


class Principal(BaseModel):
    username: str
    role: Role
    permissions: list[str] = Field(default_factory=list)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def _valid_hash(value: str) -> bool:
    parts = value.split("$")
    return (
        len(parts) == 4
        and parts[0] == "pbkdf2_sha256"
        and parts[1] == str(ITERATIONS)
        and len(parts[2]) == 32
        and len(parts[3]) == 64
        and all(c in "0123456789abcdef" for c in parts[2] + parts[3])
    )


def load_accounts() -> dict[str, Account]:
    try:
        raw = json.loads(os.environ.get("HRNOVA_AUTH_USERS", "{}"))
        if not isinstance(raw, dict) or not raw:
            raise ValueError
        accounts = {name: Account.model_validate(value) for name, value in raw.items()}
        if any(
            not name or len(name) > 100 or not _valid_hash(a.password_hash)
            for name, a in accounts.items()
        ):
            raise ValueError
        return accounts
    except (ValueError, TypeError, ValidationError):
        raise HTTPException(503, "Configuration de l’authentification indisponible.") from None


# Même calcul pour les utilisateurs inconnus afin de limiter les écarts de temps.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


def current_user(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> Principal:
    if credentials is None:
        load_accounts()
        raise HTTPException(401, "Authentification requise.", headers={"WWW-Authenticate": "Basic"})
    principal = authenticate(credentials.username, credentials.password)
    request.state.audit_details["authenticated_user"] = principal.username
    request.state.audit_details["role"] = principal.role
    return principal


def authenticate(username: str, password: str) -> Principal:
    accounts = load_accounts()
    account = accounts.get(username)
    encoded = account.password_hash if account else _DUMMY_HASH
    _, rounds, salt, expected = encoded.split("$")
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
    valid = hmac.compare_digest(actual, expected)
    if not valid or account is None or not account.enabled:
        raise HTTPException(401, "Identifiants invalides.", headers={"WWW-Authenticate": "Basic"})
    principal = Principal(
        username=username,
        role=account.role,
        permissions=sorted(PERMISSIONS[account.role]),
    )
    return principal


def require_permission(permission: str):
    def check(user: Annotated[Principal, Depends(current_user)]) -> Principal:
        if permission not in user.permissions:
            raise HTTPException(403, "Droits insuffisants.")
        return user

    return check
