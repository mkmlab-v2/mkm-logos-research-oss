"""Regression for premium multilens file-queue S1 shadow promotion gate v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = ROOT / "scripts" / "build_premium_multilens_queue_promotion_gate_v1.py"


def test_evaluate_pending_export_go_empty() -> None:
    from scripts.build_premium_multilens_queue_promotion_gate_v1 import (
        EXPORT_PENDING_SCHEMA,
        evaluate_pending_export,
    )

    snap = {"schema": EXPORT_PENDING_SCHEMA, "pending_items": []}
    dec, code, inv = evaluate_pending_export(snap)
    assert dec == "GO_PREMIUM_MULTILENS_QUEUE_S1_SHADOW"
    assert code == 0
    assert inv == 0


def test_evaluate_pending_export_hold_invalid() -> None:
    from scripts.build_premium_multilens_queue_promotion_gate_v1 import (
        EXPORT_PENDING_SCHEMA,
        evaluate_pending_export,
    )

    snap = {
        "schema": EXPORT_PENDING_SCHEMA,
        "pending_items": [
            {"job_id": "a", "validation_ok": True},
            {"job_id": "b", "validation_ok": False},
        ],
    }
    dec, code, inv = evaluate_pending_export(snap)
    assert dec == "HOLD_PREMIUM_MULTILENS_QUEUE_INVALID_PENDING"
    assert code == 1
    assert inv == 1


def test_evaluate_pending_export_wrong_schema_raises() -> None:
    from scripts.build_premium_multilens_queue_promotion_gate_v1 import evaluate_pending_export

    with pytest.raises(ValueError, match="wrong schema"):
        evaluate_pending_export({"schema": "other", "pending_items": []})


@pytest.mark.skipif(not GATE_SCRIPT.is_file(), reason="gate script missing")
def test_gate_script_skip_pytest_smoke(tmp_path: Path) -> None:
    """End-to-end: drain+export+artifact (uses repo queue stub; pytest skipped)."""
    out = tmp_path / "gate_out.json"
    export_tmp = tmp_path / "export_tmp.json"
    r = subprocess.run(
        [
            sys.executable,
            str(GATE_SCRIPT),
            "--skip-pytest",
            "--export-temp",
            str(export_tmp),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "premium_multilens_queue_promotion_gate_v1"
    assert doc.get("decision") == "GO_PREMIUM_MULTILENS_QUEUE_S1_SHADOW"
    assert doc.get("preflight", {}).get("drain_exit") == 0
    assert doc.get("preflight", {}).get("export_exit") == 0
