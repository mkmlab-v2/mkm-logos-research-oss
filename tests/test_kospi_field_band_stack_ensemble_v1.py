"""Stack ensemble + RWC shadow replay."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json").is_file(),
    reason="rwc lite missing",
)
def test_stack_ensemble_union_widen():
    from scripts.run_kospi_field_band_stack_ensemble_v1 import run_stack_ensemble
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    ev = _read(ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json")
    cal = _read(ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json")
    rwc = _read(ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json")
    cptc = _read(ROOT / "reports/kospi_field_band_cptc_lite_v1_latest.json")
    if not all((ev, cal, rwc, cptc)):
        pytest.skip("inputs missing")
    doc = run_stack_ensemble(ev, cal, rwc, cptc)
    hold = doc["summary"]["holdout_pooled"]
    stack_rate = hold["stack"]["band_hit_rate"]
    rwc_rate = hold["rwc"]["band_hit_rate"]
    assert stack_rate >= rwc_rate


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json").is_file(),
    reason="rwc lite missing",
)
def test_rwc_shadow_replay_parity():
    from scripts.run_kospi_field_band_rwc_shadow_replay_v1 import run_rwc_shadow_replay
    from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read

    ev = _read(ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json")
    cal = _read(ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json")
    fusion = _read(ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json")
    rwc = _read(ROOT / "reports/kospi_field_band_rwc_lite_v1_latest.json")
    if not all((ev, cal, fusion, rwc)):
        pytest.skip("inputs missing")
    doc = run_rwc_shadow_replay(ev, cal, fusion, rwc_doc=rwc)
    assert doc["direction_unchanged"] is True
    assert doc["summary"]["rwc_parity"]["within_tolerance"] is True


@pytest.mark.skipif(
    not (ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json").is_file(),
    reason="L2 missing",
)
def test_ack_packet_includes_conformal_metrics():
    cp = subprocess.run(
        [PY, "scripts/build_kospi_field_band_commander_ack_packet_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    pkt = json.loads(
        (ROOT / "docs/final/artifacts/kospi_field_band_commander_ack_packet_v1_latest.json").read_text(
            encoding="utf-8-sig"
        )
    )
    conf = pkt["metrics"]["conformal_stack_L2_extended"]
    assert conf.get("band_stack_union_rate") is not None
