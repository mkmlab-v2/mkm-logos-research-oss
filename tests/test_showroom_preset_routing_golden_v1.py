"""Golden routing for showroom v6 preset match (abstention, no Dan.2 fallback)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_showroom_meaning_topology_qa_presets_v1.py"
SLICE_BUILDER = ROOT / "scripts/build_showroom_meaning_topology_graph_slice_v1.py"
ERA_BUILDER = ROOT / "scripts/build_showroom_chronology_era_topology_seed_bundle_v1.py"
SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
CHRONO = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)


def _build_presets(tmp_path: Path) -> dict:
    era_bundle = tmp_path / "era_bundle.json"
    slice_out = tmp_path / "slice.json"
    out = tmp_path / "presets.json"
    for cmd in (
        [sys.executable, str(ERA_BUILDER), "--out-artifact", str(era_bundle)],
        [
            sys.executable,
            str(SLICE_BUILDER),
            "--include-job-spine",
            "--include-chronology-era-spine",
            "--era-seed-bundle",
            str(era_bundle),
            "--max-nodes",
            "320",
            "--max-edges",
            "220",
            "--out-json",
            str(slice_out),
            "--no-mirror-artifact",
        ],
    ):
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        assert proc.returncode == 0, proc.stderr or proc.stdout
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--slice-json",
            str(slice_out),
            "--chronology-json",
            str(CHRONO),
            "--no-job-reading-pack",
            "--out-mvp",
            str(out),
            "--out-artifact",
            str(tmp_path / "mirror.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def test_genesis_query_matches_era_preset(tmp_path: Path) -> None:
    from scripts.build_showroom_meaning_topology_qa_presets_v1 import match_preset_query

    doc = _build_presets(tmp_path)
    chrono = json.loads(CHRONO.read_text(encoding="utf-8"))
    hit = match_preset_query("우주 창조의 원리", doc, chrono=chrono)
    assert hit is not None
    assert hit.get("id") == "era_genesis_order_and_fall"


def test_unrelated_query_abstains_no_daniel_fallback(tmp_path: Path) -> None:
    from scripts.build_showroom_meaning_topology_qa_presets_v1 import match_preset_query

    doc = _build_presets(tmp_path)
    chrono = json.loads(CHRONO.read_text(encoding="utf-8"))
    hit = match_preset_query("테슬라 주식 옵션 만기일 전략", doc, chrono=chrono)
    assert hit is None
    fb = doc.get("fallback") or {}
    assert fb.get("abstention") is True
    assert fb.get("highlight_node_ids") == []
    dan_ids = [x for x in (fb.get("highlight_node_ids") or []) if "Dan.2" in str(x)]
    assert dan_ids == []


def test_genesis_preset_structured_answer_and_era_path(tmp_path: Path) -> None:
    doc = _build_presets(tmp_path)
    genesis = next(p for p in doc["presets"] if p.get("id") == "era_genesis_order_and_fall")
    kws = {str(k).lower() for k in genesis.get("keywords") or []}
    assert "우주" in kws
    assert "창조 원리" in kws
    assert "creation" in kws
    assert genesis.get("answer_title_ko", "").startswith("연대기 ·")
    assert genesis.get("answer_body_ko")
    assert genesis.get("slice_gap") is False
    highlights = genesis.get("highlight_node_ids") or []
    verse_hi = [h for h in highlights if not str(h).startswith("era::")]
    assert len(verse_hi) >= 2
    path_ids = genesis.get("reasoning_path_v1", {}).get("node_ids") or []
    assert path_ids
    assert "era::genesis_order_and_fall" in highlights
    leads = genesis.get("keyword_leads_ko") or {}
    assert "우주" in leads
    assert "창조 원리" in leads
