import json
from pathlib import Path
from unittest.mock import Mock

import joblib
import numpy as np
import pytest
from sklearn.dummy import DummyClassifier

from scripts.publish_huggingface import PUBLIC_KEYS, prepare_release, publish_release


@pytest.fixture
def release(tmp_path):
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
