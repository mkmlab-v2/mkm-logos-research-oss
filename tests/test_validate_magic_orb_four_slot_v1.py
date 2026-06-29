# Keywords: magic_orb, four_slot, validate, fact_lock

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def test_validate_job_insight_passes() -> None:
    from validate_magic_orb_four_slot_v1 import validate

    doc = json.loads(INSIGHT.read_text(encoding="utf-8"))
    errors = validate(doc, require_four_slot_for_job=True)
    assert errors == [], errors


def test_validate_rejects_missing_four_slot_for_job() -> None:
    from validate_magic_orb_four_slot_v1 import validate

    doc = {
        "schema": "magic_orb_question_insight_v1",
        "query": "욥이 고난을 받은 이유",
        "query_id": "job_suffering_reason",
    }
    errors = validate(doc, require_four_slot_for_job=True)
    assert any("four_slot_response_v1" in e for e in errors)


def test_validate_allows_missing_when_flagged() -> None:
    from validate_magic_orb_four_slot_v1 import validate

    doc = {
        "schema": "magic_orb_question_insight_v1",
        "query": "generic query",
        "query_id": "q01",
    }
    errors = validate(doc, require_four_slot_for_job=False)
    assert errors == []


def test_validate_cli_exit_code() -> None:
    import subprocess

    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_magic_orb_four_slot_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = json.loads(r.stdout)
    assert out["ok"] is True
