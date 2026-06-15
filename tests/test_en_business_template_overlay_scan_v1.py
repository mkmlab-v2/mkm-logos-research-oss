"""[HYPO] En business template overlay scan — B-track sandbox."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_en_business_template_overlay_scan_v1.py"
ARTIFACT = ROOT / "docs/final/artifacts/en_business_template_overlay_scan_v1_latest.json"


def test_overlay_scan_exit_zero_and_full_pass() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert ARTIFACT.is_file()
    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "en_business_template_overlay_scan_v1"
    assert doc["wire_family"] == "BIZ_MASK"
    assert doc["research_only"] is True
    agg = doc["aggregate"]
    assert agg["full_wire_and_twin_pass"] is True
    assert agg["exact_restore_rate_on_matched"] == 1.0
    assert agg["tenant_overlay_rate_on_matched"] == 1.0
    assert agg["snippet_candidates_total"] >= 14


def test_overlay_lib_tenant_terms_merge() -> None:
    from scripts.en_business_template_overlay_scan_v1_lib import tenant_overlay_terms

    shard = {
        "must_keep_hard_terms": ["invoice", "payment"],
        "must_keep_soft_terms": ["dear"],
    }
    row = {"must_keep_terms": ["contract", "invoice"]}
    terms = tenant_overlay_terms(shard, row, original_snippet="Please send invoice for payment")
    assert "invoice" in terms
    assert "payment" in terms
    assert "contract" in terms
    assert "dear" not in terms
