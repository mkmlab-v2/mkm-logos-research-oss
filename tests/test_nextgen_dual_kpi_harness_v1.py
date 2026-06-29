"""[HYPO] NextGen dual KPI harness + salience hook builder smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAV = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_NAV_FRAME_V1.json"
HOOK_BUILDER = ROOT / "scripts/build_ng40_salience_hook_from_nav_frame_v1.py"
HARNESS = ROOT / "scripts/run_nextgen_dual_kpi_harness_v1.py"
LOGOS_STACK = ROOT / "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py"
PHASE3 = ROOT / "scripts/run_nextgen_phase3_archetype_prior_chain_v1.py"
LUT_BUILDER = ROOT / "scripts/build_archetype_prior_lut_draft_v1.py"


def test_nav_frame_present() -> None:
    assert NAV.is_file()
    doc = json.loads(NAV.read_text(encoding="utf-8"))
    assert doc["schema"] == "archetype_prior_nav_frame_v1"
    assert doc["track_a_active_write"] is False
    assert doc["lut"]["status"] in ("TBD", "draft_pending_commander_signoff")


def test_salience_hook_builder_out_json(tmp_path: Path) -> None:
    out = tmp_path / "hook.json"
    cp = subprocess.run(
        [sys.executable, str(HOOK_BUILDER), "--nav-json", str(NAV), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "ng40_salience_hook_v1"
    assert doc["wired_into_ng40_codec"] is False
    assert "concept:semiconductor" in doc["concept_salience_weights"]


def test_hybrid_logos_stack_with_hook() -> None:
    out = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/_test_hybrid_logos_stack.json"
    )
    cp = subprocess.run(
        [sys.executable, str(LOGOS_STACK), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["aggregate"]["byte_exact_subset_parity"] >= 1.0
    assert doc.get("salience_hook_wired") is True
    assert doc.get("logos_terms_count", 0) >= 5


def test_phase3_archetype_prior_chain() -> None:
    cp = subprocess.run(
        [sys.executable, str(PHASE3)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr
    latest = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_archetype_prior_mask_v1_latest.json"
    )
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert doc["policy_mask_only"] is True
    assert doc["latent_codec_wired"] is False


def test_lut_draft_builder() -> None:
    cp = subprocess.run(
        [sys.executable, str(LUT_BUILDER), "--patch-nav-frame"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    draft = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
    assert draft.is_file()
    doc = json.loads(draft.read_text(encoding="utf-8"))
    assert doc["human_signoff_required"] is True
    assert doc["counts"]["finite_node_count_estimate"] >= 10


def test_guarded_b2b_decode_contract() -> None:
    script = ROOT / "scripts/run_nextgen_guarded_b2b_decode_contract_v1.py"
    cp = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    latest = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
    )
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert doc["aggregate"]["contract_met"] is True
    assert doc["aggregate"]["byte_exact_subset_parity"] >= 1.0


def test_tri_lane_bundle_merge() -> None:
    script = ROOT / "scripts/run_nextgen_tri_lane_research_bundle_v1.py"
    cp = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    latest = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_tri_lane_research_bundle_v1_latest.json"
    )
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert len(doc["lanes"]) >= 3
    assert doc["synthesis_ko"]["b2b_contract_met"] is True


def test_dual_kpi_harness_merge_only() -> None:
    cp = subprocess.run(
        [sys.executable, str(HARNESS), "--skip-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    latest = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_dual_kpi_harness_v1_latest.json"
    )
    assert latest.is_file()
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert doc["schema"] == "nextgen_dual_kpi_harness_v1"
    assert doc["track_a_active_write"] is False
    assert len(doc["arms_summary"]) >= 1
