"""ijeoma_pyobyeong_dr_pack_v1 — worktree B-track deep-research pack smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_dr_pack_exit_zero():
    proc = subprocess.run(
        [sys.executable, "scripts/build_ijeoma_pyobyeong_dr_pack_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_manifest_and_cards_schema():
    manifest = json.loads(
        (ROOT / "experiments/sasang-head-btrack/artifacts/ijeoma_pyobyeong_dr_pack_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    cards = json.loads(
        (ROOT / "experiments/sasang-head-btrack/artifacts/ijeoma_pyobyeong_insight_cards_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["schema"] == "ijeoma_pyobyeong_dr_pack_v1"
    assert manifest["send_gate"] == "HOLD"
    assert manifest["counts"]["query_count"] == 8
    assert manifest["version"] == "1.1.0"
    assert manifest["counts"]["insight_cards"] >= 9
    assert manifest["counts"]["canon_anchors"] >= 3
    assert cards["schema"] == "ijeoma_pyobyeong_insight_cards_v1"
    assert cards["version"] == "1.1.0"
    assert cards["research_only"] is True
    assert cards.get("advisory_only") is True
    ids = {c["card_id"] for c in cards["cards"]}
    assert "IC-03" in ids
    assert "IC-07" in ids
    assert "IC-08" in ids
    assert "IC-09" in ids
    assert cards.get("orthogonal_matrix_hypo_v1", {}).get("rows")
    ablation = ROOT / "experiments/sasang-head-btrack/artifacts/ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json"
    assert ablation.is_file()


def test_lit_review_exists_and_fact_lock():
    path = ROOT / "experiments/sasang-head-btrack/research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md"
    text = path.read_text(encoding="utf-8")
    assert "Fact-Lock" in text
    assert "proxy_table" in text
    assert "PBQ01" in text
    assert "CANON-" in text
    assert "v1.1" in text
    assert "IC-09" in text or "Orthogonal" in text
    tier0 = ROOT / "experiments/sasang-head-btrack/research/raw/PYOBYEONG_SASIM_SINMUL_DR_TIER0_20260629.md"
    assert tier0.is_file()


def test_query_set_dry_run():
    proc = subprocess.run(
        [sys.executable, "scripts/run_ijeoma_pyobyeong_query_set_v1.py", "--dry-run"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    summary = json.loads(
        (ROOT / "experiments/sasang-head-btrack/artifacts/ijeoma_pyobyeong_query_run_v1_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["total"] == 8
    assert summary["dry_run"] is True
