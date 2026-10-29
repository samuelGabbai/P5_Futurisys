"""Tester les décisions de déploiement sans Docker ni serveur cible."""

import pytest

from scripts import deploy_api

SOURCE = {"DATABASE_URL": "postgresql+psycopg://app:secret@db/hrnova_staging"}


def fake_docker(monkeypatch, failure=None, previous=True, rollback_failure=False):
    calls = []

    def run(args, env, capture=False):
        calls.append((args, dict(env)))
        if "ps" in args:
            return "old-container" if previous else ""
        if "--format" in args:
            return "sha256:previous"
        if failure and failure in args and env["HRNOVA_IMAGE"] != "sha256:previous":
            raise RuntimeError("échec simulé")
        if rollback_failure and "up" in args and env["HRNOVA_IMAGE"] == "sha256:previous":
            raise RuntimeError("retour arrière impossible")
        return ""

    monkeypatch.setattr(deploy_api, "run", run)
    return calls


def test_deployment_checks_database_before_replacing_service(monkeypatch):
    calls = fake_docker(monkeypatch)
    deploy_api.deploy("staging", "hrnova-api:abc", SOURCE)
    preflight = next(i for i, (args, _) in enumerate(calls) if "run" in args)
    up = next(i for i, (args, _) in enumerate(calls) if "up" in args)
    assert preflight < up
    assert any("exec" in args for args, _ in calls)
    assert all(env["APP_ENV"] == "staging" and env["API_PORT"] == "8002" for _, env in calls)
    assert all("hrnova-staging" in args for args, _ in calls if "compose" in args)
    assert all(SOURCE["DATABASE_URL"] not in arg for args, _ in calls for arg in args)


def test_database_failure_preserves_running_api(monkeypatch):
    calls = fake_docker(monkeypatch, failure="run")
    with pytest.raises(RuntimeError):
        deploy_api.deploy("staging", "hrnova-api:abc", SOURCE)
    assert not any("up" in args or "stop" in args for args, _ in calls)


@pytest.mark.parametrize("failure", ["up", "exec"])
def test_failed_health_or_inference_restores_exact_previous_image(monkeypatch, failure):
    calls = fake_docker(monkeypatch, failure=failure)
    with pytest.raises(RuntimeError, match="image précédente restaurée"):
        deploy_api.deploy("staging", "hrnova-api:abc", SOURCE)
    assert calls[-1][1]["HRNOVA_IMAGE"] == "sha256:previous"
    assert "up" in calls[-1][0]


def test_first_failure_stops_unhealthy_instance(monkeypatch):
    calls = fake_docker(monkeypatch, failure="exec", previous=False)
    with pytest.raises(RuntimeError, match="instance arrêtée"):
        deploy_api.deploy("development", "hrnova-api:abc", SOURCE)
    assert "stop" in calls[-1][0]


def test_rollback_failure_is_reported(monkeypatch):
    fake_docker(monkeypatch, failure="exec", rollback_failure=True)
    with pytest.raises(RuntimeError, match="intervention requise"):
        deploy_api.deploy("production", "hrnova-api:abc", SOURCE)


@pytest.mark.parametrize(
    "environment,image,source",
    [
        ("unknown", "hrnova-api:abc", SOURCE),
        ("staging", "--bad", SOURCE),
        ("staging", "hrnova-api:abc", {}),
        ("staging", "hrnova-api:abc", {**SOURCE, "API_PORT": "70000"}),
        ("staging", "hrnova-api:abc", {"DATABASE_URL": "postgresql+psycopg://u:CHANGE_ME@db/base"}),
    ],
)
def test_bad_configuration_never_calls_docker(monkeypatch, environment, image, source):
    calls = fake_docker(monkeypatch)
    with pytest.raises(ValueError):
        deploy_api.deploy(environment, image, source)
    assert calls == []


@pytest.mark.parametrize("registered,mismatch", [(True, False), (False, False), (True, True)])
def test_preflight_requires_registered_compatible_model(
    monkeypatch, tmp_path, registered, mismatch
):
    import hashlib

    import joblib

    from database import ModelVersion, session
    from scripts.check_deployment import check

    path = tmp_path / "model.joblib"
    joblib.dump(
        {"feature_names": ["feature_a", "feature_b"], "threshold": 0.6, "positive_class": 1}, path
    )
    monkeypatch.setenv("HRNOVA_MODEL_PATH", str(path))
    if registered:
        with session() as db, db.begin():
            db.add(
                ModelVersion(
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    feature_names=["unexpected"] if mismatch else ["feature_a", "feature_b"],
                    threshold=0.6,
                    positive_class=1,
                )
            )
    if not registered or mismatch:
        with pytest.raises(ValueError):
            check()
    else:
        check()
