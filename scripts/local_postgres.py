"""Instance PostgreSQL locale isolée, sans modification de l'installation système."""

import argparse
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
DATA = LOCAL / "postgres"
ADMIN_ENV = LOCAL / "admin.env"


def run(*args, **kwargs):
    subprocess.run([str(arg) for arg in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["start", "stop", "status", "recreate"], default="start", nargs="?"
    )
    parser.add_argument("--pg-bin", type=Path, default=Path("/Library/PostgreSQL/18/bin"))
    args = parser.parse_args()
    binary = args.pg_bin
    if args.action in {"stop", "status"}:
        run(binary / "pg_ctl", "-D", DATA, args.action)
        return
    LOCAL.mkdir(mode=0o700, exist_ok=True)
    if not ADMIN_ENV.exists():
        if (ROOT / ".env").exists() or DATA.exists():
            raise SystemExit(
                "Configuration locale existante : utilisez votre DATABASE_URL avec create_db.py."
            )
        admin_password, app_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        ADMIN_ENV.write_text(f"ADMIN_PASSWORD={admin_password}\nAPP_PASSWORD={app_password}\n")
        ADMIN_ENV.chmod(0o600)
    config = dotenv_values(ADMIN_ENV)
    if not (DATA / "PG_VERSION").exists():
        password_file = LOCAL / "init-password"
        password_file.write_text(config["ADMIN_PASSWORD"])
        password_file.chmod(0o600)
        try:
            run(
                binary / "initdb",
                "-D",
                DATA,
                "-U",
                "hrnova_admin",
                "--pwfile",
                password_file,
                "--auth-local=scram-sha-256",
                "--auth-host=scram-sha-256",
                "--encoding=UTF8",
                "--locale=C",
            )
        finally:
            password_file.unlink(missing_ok=True)
        with (DATA / "postgresql.conf").open("a") as stream:
            stream.write(
                "\nlisten_addresses = '127.0.0.1'\nport = 5433\nunix_socket_directories = ''\n"
            )
    running = (
        subprocess.run(
            [str(binary / "pg_ctl"), "-D", str(DATA), "status"], capture_output=True
        ).returncode
        == 0
    )
    if not running:
        run(binary / "pg_ctl", "-D", DATA, "-l", LOCAL / "postgres.log", "-w", "start")
    if args.action == "recreate":
        with psycopg.connect(
            host="127.0.0.1",
            port=5433,
            user="hrnova_admin",
            password=config["ADMIN_PASSWORD"],
            dbname="postgres",
            connect_timeout=5,
            autocommit=True,
        ) as connection:
            exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = 'hrnova'"
            ).fetchone()
            if exists:
                backups = LOCAL / "backups"
                backups.mkdir(mode=0o700, exist_ok=True)
                backup = backups / (
                    "hrnova_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".dump"
                )
                run(
                    binary / "pg_dump",
                    "-h",
                    "127.0.0.1",
                    "-p",
                    "5433",
                    "-U",
                    "hrnova_admin",
                    "-d",
                    "hrnova",
                    "-Fc",
                    "-f",
                    backup,
                    env=dict(os.environ, PGPASSWORD=config["ADMIN_PASSWORD"]),
                )
                backup.chmod(0o600)
                print(f"Sauvegarde conservée : {backup.relative_to(ROOT)}")
                connection.execute("DROP DATABASE hrnova WITH (FORCE)")
    admin_url = (
        f"postgresql+psycopg://hrnova_admin:{config['ADMIN_PASSWORD']}@127.0.0.1:5433/hrnova"
    )
    env = dict(os.environ, DATABASE_URL=admin_url)
    # subprocess n'affiche pas l'URL ni le mot de passe.
    run(sys.executable, ROOT / "create_db.py", "--create-database", env=env, cwd=ROOT)
    connection_kwargs = dict(
        host="127.0.0.1",
        port=5433,
        user="hrnova_admin",
        password=config["ADMIN_PASSWORD"],
        dbname="hrnova",
    )
    with psycopg.connect(**connection_kwargs) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = 'hrnova_app'"
        ).fetchone()
        if not exists:
            connection.execute(
                sql.SQL(
                    "CREATE ROLE hrnova_app LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE"
                ).format(sql.Literal(config["APP_PASSWORD"]))
            )
        connection.execute("REVOKE ALL ON DATABASE hrnova FROM PUBLIC")
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.execute("GRANT CONNECT ON DATABASE hrnova TO hrnova_app")
        connection.execute("GRANT USAGE ON SCHEMA public TO hrnova_app")
        connection.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO hrnova_app")
        connection.execute(
            "GRANT INSERT ON api_exchanges, model_inputs, model_outputs TO hrnova_app"
        )
        connection.execute("GRANT UPDATE ON api_exchanges TO hrnova_app")
        connection.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO hrnova_app")
    env_file = ROOT / ".env"
    if not env_file.exists():
        env_file.write_text(
            f"DATABASE_URL=postgresql+psycopg://hrnova_app:{config['APP_PASSWORD']}@127.0.0.1:5433/hrnova\nHRNOVA_MODEL_PATH=artifacts/turnover_model.joblib\n"
        )
        env_file.chmod(0o600)
    print("PostgreSQL prêt : 127.0.0.1:5433/hrnova. Configuration applicative dans .env.")


if __name__ == "__main__":
    main()
