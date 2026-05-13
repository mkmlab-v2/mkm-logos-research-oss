"""Integration: build_logos_insight_bundle_v1 assembles valid logos_insight_bundle_v1 JSON."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]


def _write_fixtures(tmp: Path) -> dict[str, Path]:
    morph = {
        "schema": "logos_morphology_registry_v1",
        "morphology_layer": {
            "registry_id": "morphhb_hebrew_core_v1",
            "hebrew_atoms_total": 100,
            "matched_hebrew_atoms": 80,
            "unmatched_hebrew_atoms": 20,
            "coverage_ratio_0_1": 0.8,
            "sampled_matched_rows": 10,
            "sampled_scanned_lines": 50,
        },
    }
    sem = {
        "schema": "aramaic_semantic_edge_quality_v1",
        "edge_count": 4,
        "semantic_overlap_mean": 0.35,
        "shared_token_mean": 1.5,
        "edge_type_histogram": {"cross_lens_confirm": 4},
    }
    insight = {
        "schema": "bible_meaning_insight_candidates_v1",
        "candidates": [],
    }
    edge = {
        "schema": "aramaic_graph_edge_v1",
        "src_node_id": "aramaic::dan_1_1",
        "dst_node_id": "hebrew::dan_1_1",
        "edge_type": "cross_lens_confirm",
        "weight": 0.82,
        "source_track": "B",
    }
    regime = {"schema": "aramaic_regime_shift_score_v1", "score_label": "shadow", "shadow_score_0_1": 0.4}

    p_m = tmp / "morph.json"
    p_s = tmp / "sem.json"
    p_i = tmp / "insight.json"
    p_b = tmp / "bridge.jsonl"
    p_r = tmp / "regime.json"
    p_m.write_text(json.dumps(morph, ensure_ascii=False), encoding="utf-8")
    p_s.write_text(json.dumps(sem, ensure_ascii=False), encoding="utf-8")
    p_i.write_text(json.dumps(insight, ensure_ascii=False), encoding="utf-8")
    p_b.write_text(json.dumps(edge, ensure_ascii=False) + "\n", encoding="utf-8")
    p_r.write_text(json.dumps(regime, ensure_ascii=False), encoding="utf-8")
    return {"morph": p_m, "sem": p_s, "insight": p_i, "bridge": p_b, "regime": p_r}


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_insight_bundle_cli_outputs_valid_schema(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path)
    out = tmp_path / "bundle.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_insight_bundle_v1.py"),
        "--out",
        str(out),
        "--morphology-json",
        str(paths["morph"]),
        "--semantic-quality-json",
        str(paths["sem"]),
        "--insight-candidates-json",
        str(paths["insight"]),
        "--bridge-edges-jsonl",
        str(paths["bridge"]),
        "--regime-shift-json",
        str(paths["regime"]),
        "--top-k",
        "4",
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout

    bundle = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=bundle, schema=schema)

    assert bundle["degraded"] is False
    assert bundle["missing_upstream"] == []
    assert bundle["aggregation"]["morphology_summary"]["matched_hebrew_atoms"] == 80
    assert len(bundle["tension_hypotheses"]) >= 1
    assert any(
        h.get("tension_axis_id") == "bridge_edges_present_insight_candidates_absent_v0"
        for h in bundle["tension_hypotheses"]
    )


@pytest.mark.skipif(jsonschema is None, reason="jsonschema not installed")
def test_build_logos_insight_bundle_all_missing_still_valid(tmp_path: Path) -> None:
    out = tmp_path / "empty_bundle.json"
    missing = tmp_path / "nope.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_insight_bundle_v1.py"),
        "--out",
        str(out),
        "--morphology-json",
        str(missing),
        "--semantic-quality-json",
        str(missing),
        "--insight-candidates-json",
        str(missing),
        "--bridge-edges-jsonl",
        str(missing),
        "--regime-shift-json",
        str(missing),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr + r.stdout
    bundle = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "docs/final/schemas/logos_insight_bundle_v1.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=bundle, schema=schema)
    assert bundle["degraded"] is True
    assert len(bundle["missing_upstream"]) == 5
    assert bundle["aggregation"] == {}
    assert bundle["tension_hypotheses"] == []
