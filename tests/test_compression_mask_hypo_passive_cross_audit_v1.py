"""[HYPO-4] MASK HYPO passive cross-audit chain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_compression_mask_hypo_passive_cross_audit_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/compression_mask_hypo_passive_cross_audit_v1_latest.json"


def test_passive_cross_audit_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_mask_hypo_passive_cross_audit_v1"
    assert doc["non_gating"] is True
    assert doc["input_policy"] == "masked_corpus_jsonl_replay_only"
    agg = doc["aggregate"]
    assert agg["all_steps_pass"] is True
    assert agg["step_count"] == 5
    assert agg["mask_step_count"] == 4
    assert agg["coord_sibling_included"] is True
    assert doc.get("coord_sibling", {}).get("step_id") == "rib55_coord_passive"
    assert doc.get("coord_sibling", {}).get("axis") == "SKU-COORD"


def test_chain_step_metadata() -> None:
    from scripts.compression_mask_hypo_passive_cross_audit_v1_lib import CHAIN_STEPS

    ids = [s["step_id"] for s in CHAIN_STEPS]
    assert ids == ["registry_sync", "biz_overlay", "biz_shadow_bind", "cs_wtt_overlay"]
