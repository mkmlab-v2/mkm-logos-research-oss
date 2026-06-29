#!/usr/bin/env python3
"""Physics-alignment HYPO chain — lexicon validate + HG-6 primitive report.

Does NOT modify gematria_bridge_v1 kernel.

Reproducible:
  py scripts/run_logos_physics_alignment_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEXICON = ROOT / "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json"
SCHEMA = ROOT / "docs/final/schemas/logos_fundamental_force_lexicon_v1.schema.json"
REPORT = ROOT / "docs/final/artifacts/logos_fundamental_force_primitive_report_v1_latest.json"


def validate_lexicon() -> None:
    jsonschema = __import__("jsonschema")
    doc = json.loads(LEXICON.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
    if doc.get("kernel_recipe_id") != "gematria_bridge_v1":
        raise SystemExit("lexicon must not override kernel recipe")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    validate_lexicon()
    print("OK: lexicon schema validate")

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_fundamental_force_primitive_report_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    print("OK: build_logos_fundamental_force_primitive_report_v1.py")

    if not args.skip_pytest:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_logos_fundamental_force_lexicon_v1.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest")

    assert REPORT.is_file()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
