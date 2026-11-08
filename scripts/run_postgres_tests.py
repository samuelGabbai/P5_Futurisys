"""Exécuter Pytest dans une base PostgreSQL jetable du serveur local du projet."""

import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]


def run_tests(pytest_args):
    config = dotenv_values(ROOT / ".local/admin.env")
    password = config.get("ADMIN_PASSWORD")
    if not password:
        raise ValueError("Initialiser PostgreSQL avec scripts/local_postgres.py start.")
    name = "hrnova_pytest_" + uuid4().hex
    with psycopg.connect(
        host="127.0.0.1",
        port=5433,
        dbname="postgres",
        user="hrnova_admin",
        password=password,
        autocommit=True,
        connect_timeout=5,
    ) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            url = URL.create(
                "postgresql+psycopg",
                username="hrnova_admin",
                password=password,
                host="127.0.0.1",
                port=5433,
                database=name,
            )
            env = dict(
                os.environ,
                TEST_DATABASE_URL=url.render_as_string(hide_password=False),
                PYTHONDONTWRITEBYTECODE="1",
            )
            return subprocess.run(
                [sys.executable, "-m", "pytest", *pytest_args], cwd=ROOT, env=env
            ).returncode
        finally:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


if __name__ == "__main__":
    try:
        result = run_tests(sys.argv[1:])
    except Exception:
        print(
            "Tests PostgreSQL impossibles : contrôler le serveur et les identifiants locaux.",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(result)
