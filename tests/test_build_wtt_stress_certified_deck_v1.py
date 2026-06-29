"""Stress Certified internal deck builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_stress_certified_deck_v1.py"
FSM = ROOT / "reports/wtt_spicy_corpus_fsm_batch_v1_latest.json"
TUNE = ROOT / "reports/wtt_dialog_risk_policy_tune_v1_latest.json"


def test_build_stress_deck(tmp_path: Path) -> None:
    if not FSM.is_file() or not TUNE.is_file():
        import pytest

        pytest.skip("FSM/tune reports missing — run solo auto or spicy batch first")

    out_md = tmp_path / "deck.md"
    out_meta = tmp_path / "deck.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out",
            str(out_md),
            "--meta-out",
            str(out_meta),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out_md.read_text(encoding="utf-8")
    assert "Stress Certified" in text
    assert "SEND HOLD" in text
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("research_only") is True
    assert meta.get("send_gate") == "HOLD"


def test_build_stress_deck_operator_panel_appendix(tmp_path: Path) -> None:
    if not FSM.is_file() or not TUNE.is_file():
        import pytest

        pytest.skip("FSM/tune reports missing")
    gate = ROOT / "reports/wtt_operator_panel_gate_v1_latest.json"
    op_fsm = ROOT / "reports/wtt_operator_panel_fsm_batch_v1_latest.json"
    if not gate.is_file() or not op_fsm.is_file():
        import pytest

        pytest.skip("operator panel gate/fsm missing — run Invoke-WttOperatorPanelDeckRefresh_v1.ps1")

    out_md = tmp_path / "deck_op.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out",
            str(out_md),
            "--meta-out",
            str(tmp_path / "deck_op.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out_md.read_text(encoding="utf-8")
    assert "Internal panel v0" in text
    assert "30/30" in text or "operator_panel_n30_gate_met" in text
    meta = json.loads((tmp_path / "deck_op.json").read_text(encoding="utf-8"))
    assert meta.get("operator_panel_appendix_included") is True


def test_build_stress_deck_customer_lane_appendix(tmp_path: Path) -> None:
    if not FSM.is_file() or not TUNE.is_file():
        import pytest

        pytest.skip("FSM/tune reports missing")
    human = ROOT / "reports/wtt_human_n30_gate_v1_latest.json"
    cust_fsm = ROOT / "reports/wtt_tenant_fsm_batch_wtt-customer-live-v1_v1_latest.json"
    if not human.is_file() or not cust_fsm.is_file():
        import pytest

        pytest.skip("customer lane gate/fsm missing")

    out_md = tmp_path / "deck_cust.md"
    out_meta = tmp_path / "deck_cust.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out",
            str(out_md),
            "--meta-out",
            str(out_meta),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out_md.read_text(encoding="utf-8")
    assert "Premium CS customer lane" in text
    assert "human_n30_gate_met" in text
    meta = json.loads(out_meta.read_text(encoding="utf-8"))
    assert meta.get("customer_lane_appendix_included") is True


def test_build_stress_deck_rq025_appendix(tmp_path: Path) -> None:
    if not FSM.is_file() or not TUNE.is_file():
        import pytest

        pytest.skip("FSM/tune reports missing")
    auto = ROOT / "reports/rq025_upstream_csv_auto_resolve_v1_latest.json"
    three = ROOT / "reports/rq025_lambda_source_three_arm_compare_v1_latest.json"
    if not auto.is_file() or not three.is_file():
        import pytest

        pytest.skip("RQ-025 auto-resolve reports missing")

    out_md = tmp_path / "deck_rq025.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--out",
            str(out_md),
            "--meta-out",
            str(tmp_path / "deck_rq025.json"),
            "--include-rq025-appendix",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = out_md.read_text(encoding="utf-8")
    assert "Appendix — Oracle RQ-025" in text
    assert "합성 데이터 기반 벤치" in text
    assert "Proof (synthetic spicy 25" in text
