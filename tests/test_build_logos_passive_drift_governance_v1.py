from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_logos_passive_drift_governance_v1.py"
HOLDOUT = ROOT / "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json"
OFF_AB = ROOT / "reports/logos_chronology_off_fixture_text_blind_v2_ab_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_passive_drift_governance_v1_latest.json"


def test_build_logos_passive_drift_governance_v1_runs() -> None:
    assert HOLDOUT.is_file(), "missing holdout artifact"
    assert OFF_AB.is_file(), "missing off-fixture AB artifact"
    rc = subprocess.call([sys.executable, str(BUILD), "--no-history"], cwd=str(ROOT))
    assert rc == 0
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_passive_drift_governance_v1"
    assert doc["policy"]["auto_apply_text_blind_v2"] is False
    cohorts = doc["cohorts"]
    assert "train_holdout" in cohorts
    assert "off_fixture_ab" in cohorts
    off_delta = cohorts["off_fixture_ab"].get("delta_v2_minus_v1")
    assert off_delta == 0.0
    guard = cohorts.get("guardrails_ko") or []
    assert any("85.1%" in g for g in guard)
    assert doc["lexicon_rail"]["clinical_cds_merge_forbidden"] is True
    assert doc["measurement_loop"]["schema"] == "logos_measurement_loop_v1"


def test_chain_fast_smoke() -> None:
    rc = subprocess.call(
        [sys.executable, str(ROOT / "scripts/run_logos_passive_drift_governance_chain_v1.py"), "--fast"],
        cwd=str(ROOT),
    )
    assert rc == 0
    manifest = ROOT / "reports/logos_passive_drift_governance_chain_v1_latest.json"
    assert manifest.is_file()
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["ok"] is True
