import json
import os
from pathlib import Path
from unittest.mock import Mock

import joblib
import numpy as np
import pytest
from sklearn.dummy import DummyClassifier

from scripts.publish_huggingface import PUBLIC_KEYS, prepare_release, publish_release


@pytest.fixture
def release(tmp_path, monkeypatch):
    from auth import hash_password

    monkeypatch.setenv(
        "HRNOVA_AUTH_USERS",
        json.dumps(
            {
                "delivery": {
                    "password_hash": hash_password("delivery-test-password"),
                    "role": "livreur",
                }
            }
        ),
    )
    monkeypatch.setenv("HRNOVA_DELIVERY_USERNAME", "delivery")
    monkeypatch.setenv("HRNOVA_DELIVERY_PASSWORD", "delivery-test-password")
    model = DummyClassifier(strategy="prior").fit([[1, 2], [3, 4]], [0, 1])
    source = tmp_path / "original.joblib"
    joblib.dump(
        {
            "model": model,
            "threshold": 0.6,
            "feature_names": ["age", "income"],
            "positive_class": 1,
            "records_by_employee_id": {"42": {"age": 33, "income": 2500}},
            "another_private_field": "NEVER_PUBLISH",
        },
        source,
    )
    output = tmp_path / "release"
    metadata = prepare_release(source, output, "commit-123")
    return source, output, metadata


def test_export_removes_employee_records_without_changing_model(release):
    source, output, metadata = release
    original = joblib.load(source)
    exported = joblib.load(output / "turnover_model.joblib")
    assert set(exported) == PUBLIC_KEYS
    assert "records_by_employee_id" in original
    assert exported["threshold"] == 0.6
    np.testing.assert_array_equal(
        original["model"].predict_proba([[5, 6]]), exported["model"].predict_proba([[5, 6]])
    )
    assert metadata["git_sha"] == "commit-123"
    assert metadata["source_sha256"] != metadata["model_sha256"]
    assert "records_by_employee_id" not in json.dumps(metadata)
    assert "NEVER_PUBLISH" not in (output / "metadata.json").read_text()


def test_publish_uploads_only_allowed_files_to_existing_model_repo(release):
    _, output, _ = release
    client = Mock()
    publish_release(output, "account/hrnova", "test-token", "commit-123", client=client)
    kwargs = client.upload_folder.call_args.kwargs
    assert kwargs["repo_id"] == "account/hrnova"
    assert kwargs["repo_type"] == "model"
    assert set(kwargs["allow_patterns"]) == {
        "turnover_model.joblib",
        "metadata.json",
        "README.md",
        "requirements.txt",
    }
    assert "commit-123" in kwargs["commit_message"]
    client.create_repo.assert_not_called()


@pytest.mark.parametrize(
    "failure", ["changed-model", "wrong-commit", "extra-file", "missing-token"]
)
def test_invalid_release_never_contacts_huggingface(release, failure):
    _, output, _ = release
    token, commit = "test-token", "commit-123"
    if failure == "changed-model":
        (output / "turnover_model.joblib").write_bytes(b"changed")
    elif failure == "wrong-commit":
        commit = "another-commit"
    elif failure == "extra-file":
        (output / "private.csv").write_text("private data")
    else:
        token = ""
    client = Mock()
    with pytest.raises(ValueError):
        publish_release(output, "account/hrnova", token, commit, client=client)
    client.upload_folder.assert_not_called()


def test_prepare_preserves_source_and_refuses_same_directory(release):
    source, _, _ = release
    original = source.read_bytes()
    with pytest.raises(ValueError):
        prepare_release(source, source.parent, "commit-123")
    assert source.read_bytes() == original


@pytest.mark.parametrize("role", ["utilisateur", "lecteur", "analyste"])
def test_api_role_cannot_publish_even_with_huggingface_token(release, monkeypatch, role):
    _, output, _ = release
    accounts = json.loads(os.environ["HRNOVA_AUTH_USERS"])
    accounts["delivery"]["role"] = role
    monkeypatch.setenv("HRNOVA_AUTH_USERS", json.dumps(accounts))
    client = Mock()
    with pytest.raises(PermissionError, match="Droit de livraison"):
        publish_release(output, "account/hrnova", "valid-token", "commit-123", client=client)
    client.upload_folder.assert_not_called()


@pytest.mark.parametrize("failure", ["wrong-password", "disabled", "missing-config"])
def test_unauthenticated_delivery_never_contacts_huggingface(release, monkeypatch, failure):
    _, output, _ = release
    if failure == "wrong-password":
        monkeypatch.setenv("HRNOVA_DELIVERY_PASSWORD", "wrong")
    elif failure == "missing-config":
        monkeypatch.delenv("HRNOVA_AUTH_USERS")
    else:
        accounts = json.loads(os.environ["HRNOVA_AUTH_USERS"])
        accounts["delivery"]["enabled"] = False
        monkeypatch.setenv("HRNOVA_AUTH_USERS", json.dumps(accounts))
    client = Mock()
    with pytest.raises(PermissionError, match="Authentification"):
        publish_release(output, "account/hrnova", "valid-token", "commit-123", client=client)
    client.upload_folder.assert_not_called()


@pytest.mark.parametrize(
    "field,value,message",
    [
        (None, [], "métadonnées"),
        (None, {}, "métadonnées"),
        ("feature_names", [], "variables"),
        ("feature_names", ["age", "age"], "variables"),
        ("feature_names", [None], "variables"),
        ("model", None, "predict"),
        ("threshold", float("nan"), "Seuil ou classes"),
        ("threshold", 1.1, "Seuil ou classes"),
        ("positive_class", 2, "Seuil ou classes"),
    ],
)
def test_invalid_source_cannot_create_release(release, tmp_path, field, value, message):
    source, _, _ = release
    bundle = joblib.load(source)
    if field is None:
        bundle = value
    else:
        bundle[field] = value
    joblib.dump(bundle, source)
    before = source.read_bytes()
    destination = tmp_path / "rejected"
    with pytest.raises(ValueError, match=message):
        prepare_release(source, destination, "commit-123")
    assert source.read_bytes() == before
    assert not destination.exists()


def test_missing_commit_and_nonempty_destination_preserve_files(release):
    source, output, _ = release
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    for commit, message in [("  ", "commit Git"), ("commit-123", "doit être vide")]:
        with pytest.raises(ValueError, match=message):
            prepare_release(source, output, commit)
        assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_publication_constructs_sdk_client_without_network(release, monkeypatch):
    import sys
    from types import ModuleType

    _, output, _ = release
    sdk = ModuleType("huggingface_hub")
    client = Mock()
    client.upload_folder.return_value = "mock-commit-url"
    sdk.HfApi = Mock(return_value=client)
    monkeypatch.setitem(sys.modules, "huggingface_hub", sdk)
    assert (
        publish_release(output, "account/hrnova", "test-token", "commit-123") == "mock-commit-url"
    )
    sdk.HfApi.assert_called_once_with(token="test-token")
    client.upload_folder.assert_called_once_with(
        repo_id="account/hrnova",
        repo_type="model",
        revision="main",
        folder_path=str(output),
        allow_patterns=sorted(
            ["turnover_model.joblib", "metadata.json", "README.md", "requirements.txt"]
        ),
        commit_message="Modèle HRNova — Git commit-123",
    )
