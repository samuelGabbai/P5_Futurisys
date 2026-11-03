"""Préparer et livrer le modèle avec un compte autorisé."""

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from model_release import (
    DEFAULT_REPO_ID,
    MODEL_FILE,
    PUBLIC_KEYS,
    RELEASE_FILES,
    prepare_release,
    publish_release,
    sha256,
)

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--model-path", type=Path, default=Path("artifacts") / MODEL_FILE)
    parser.add_argument("--output-dir", type=Path, default=Path("hf-release"))
    parser.add_argument("--git-sha", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args()
    if args.prepare_only:
        metadata = prepare_release(args.model_path, args.output_dir, args.git_sha)
        print(f"Export préparé : {metadata['model_sha256']} (commit {metadata['git_sha']}).")
    else:
        repo_id = os.environ.get("HF_REPO_ID") or DEFAULT_REPO_ID
        try:
            publish_release(
                args.output_dir,
                repo_id,
                os.environ.get("HF_TOKEN", ""),
                args.git_sha,
            )
        except PermissionError as error:
            parser.exit(1, f"{error}\n")
        print(f"Modèle publié : https://huggingface.co/{repo_id}")


if __name__ == "__main__":
    main()
