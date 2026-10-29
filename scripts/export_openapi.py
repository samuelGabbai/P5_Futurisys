"""Exporter le contrat FastAPI sans démarrer l'API ni ouvrir de connexion BDD."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/openapi.json")
    args = parser.parse_args()
    schema = app.openapi()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Contrat OpenAPI exporté : {len(schema['paths'])} endpoints, {args.output}.")


if __name__ == "__main__":
    main()
