"""Committed defense JSON artifacts: shape invariants (no benchmark runs)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.defense_code_pack_v1 import load_code_pack, verify_linked_artifacts  # noqa: E402


def _load(name: str) -> dict:
    p = ART / name
    assert p.is_file(), f"missing {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def test_snapshot_table_schema() -> None:
    doc = _load("DEFENSE_BENCH_SNAPSHOT_TABLE_V1.json")
    assert doc.get("schema") == "defense_bench_snapshot_table_v1"
    rows = doc.get("rows") or []
    lanes = {r.get("lane") for r in rows}
    assert "track_a_universal" in lanes
    assert "defense_hybrid_uav_synthetic" in lanes
    for lane in ("track_a_universal", "defense_hybrid_uav_synthetic"):
        row = next(r for r in rows if r.get("lane") == lane)
        assert row.get("artifact")

    merged_path = ART / "defense_hybrid_compression_bench_merged_v0.json"
    sources = doc.get("sources") or {}
    if merged_path.is_file():
        assert sources.get("hybrid_merged")
        assert "defense_hybrid_uav_synthetic_merged" in lanes
        mrow = next(r for r in rows if r.get("lane") == "defense_hybrid_uav_synthetic_merged")
        assert mrow.get("stress_input_appended")


def test_briefing_bullets_schema() -> None:
    doc = _load("DEFENSE_BENCH_BRIEFING_BULLETS_V1.json")
    assert doc.get("schema") == "defense_bench_briefing_bullets_v1"
    ko = doc.get("briefing_bullets_ko") or []
    en = doc.get("briefing_bullets_en") or []
    assert len(ko) == 5 and all(isinstance(s, str) and s.strip() for s in ko)
    assert len(en) == 5 and all(isinstance(s, str) and s.strip() for s in en)


def test_bridge_by_mode_schema() -> None:
    doc = _load("MULTILENS_BRIDGE_POLICY_AB_BY_MODE_V1.json")
    assert doc.get("schema") == "multilens_bridge_policy_ab_by_mode_v1"
    modes = doc.get("modes") or {}
    for key in ("universal", "literal", "ultra_literal"):
        assert key in modes
        m = modes[key]
        for side in ("bridge_off", "bridge_on"):
            cms = (m.get(side) or {}).get("compression_metrics_summary") or {}
            assert "global_token_saving_rate" in cms
            assert "avg_reconstruction_fidelity_jaccard" in cms


def test_defense_code_pack_linked_paths_exist() -> None:
    doc = load_code_pack()
    rows = verify_linked_artifacts(doc, ROOT)
    missing = [r["path"] for r in rows if not r["exists"]]
    assert not missing, f"missing: {missing}"


def test_pitch_codepack_embeds_briefing_bullets() -> None:
    p = ART / "defense_pitch_codepack_v1.json"
    assert p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))
    bb = doc.get("briefing_bullets") or {}
    assert bb.get("schema") == "defense_bench_briefing_bullets_v1"
    assert len(bb.get("briefing_bullets_ko") or []) == 5
    assert len(bb.get("briefing_bullets_en") or []) == 5
    src = (doc.get("build") or {}).get("sources") or {}
    assert src.get("briefing_bullets_json") == "docs/final/artifacts/DEFENSE_BENCH_BRIEFING_BULLETS_V1.json"


def test_uav_stress_input_schema() -> None:
    doc = _load("defense_uav_bench_stress_v0.json")
    assert doc.get("schema") == "defense_uav_bench_input_v0"
    recs = doc.get("records") or []
    assert len(recs) == doc.get("record_count") == 8
    ids = [r.get("id") for r in recs]
    assert ids == [f"stress_{i:03d}" for i in range(8)]
    for r in recs:
        assert "location" in r and "lat" in (r.get("location") or {})
        assert "situational_text" in r
        assert isinstance(r.get("situational_text"), str)
