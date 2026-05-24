"""Universal Matrix bench — B-track lane; Golden 40 isolation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/universal_compression_bench_matrix_registry_v1.json"
GOLDEN = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
MATRIX = ROOT / "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json"
BUILD = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_build_v1.json"


def test_registry_and_pointer_exist():
    assert REGISTRY.is_file()
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert reg["golden_set_frozen"]["bench_label"] == "full_v2_40"
    assert reg["research_only"] is True
    lane_ids = [str(ln.get("lane_id")) for ln in reg.get("lanes") or []]
    assert "ijeoma_chunk_cjk_hypo_v1" in lane_ids
    ptr = ROOT / "data/compression/bench/universal_matrix_v1/CANONICAL_POINTER_V1.json"
    assert ptr.is_file()


def test_build_matrix_lanes_only_does_not_touch_golden():
    before = GOLDEN.read_text(encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/build_universal_compression_bench_matrix_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    after = GOLDEN.read_text(encoding="utf-8")
    assert before == after
    assert MATRIX.is_file()
    doc = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert doc["case_count"] >= 470
    assert doc["golden_included"] is False
    ids = {c["id"] for c in doc["compression_cases"]}
    assert not any(i.startswith("cmp2_") for i in ids)
    assert any(i.startswith("finance_macro_b2b_v1__") for i in ids)


def test_build_report_written():
    assert BUILD.is_file()
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    assert build["golden_do_not_modify"] is True
    assert build["case_count"] >= 71


def test_sweep_dry_run():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_universal_compression_bench_matrix_sweep_v1.py",
            "--dry-run",
            "--max-cases",
            "3",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_sweep_exclude_chunk_lane_dry_run():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_universal_compression_bench_matrix_sweep_v1.py",
            "--dry-run",
            "--exclude-lane-id",
            "ijeoma_chunk_table_v1",
            "--exclude-lane-id",
            "ijeoma_chunk_cjk_hypo_v1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    line = proc.stdout.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["case_count"] == 290
    assert "ijeoma_chunk_table_v1" in data["excluded_lane_ids"]


def test_wire_ab_290_subset_weighted():
    path = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_summary_290_subset_v1.json"
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["case_count"] == 290
    wh = doc["weighted_headline"]
    assert wh["bridge_boost_cases"] == 209
    assert 0.5 < wh["delta_jaccard_pp"] < 2.0


def test_hanja_hypo_scan_artifact():
    path = ROOT / "reports/constitution/btrack_pilot/comp_hanja_codebook_coverage_hypo_scan_v1.json"
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["hypothesis_tier"] == "B"
    hits = doc["eval_lexicon_hits_per_case"]
    if "min_token_len_2" in hits:
        assert hits["min_token_len_2"]["mean"] == 0.0
        assert hits["min_token_len_1"]["mean"] == 0.0
    else:
        assert hits["mean"] == 0.0


def test_sweep_290_subset_artifact_exists():
    path = ROOT / "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_290_subset_v1.json"
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["case_count"] == 290
    assert doc["headline"]["economy_mean_saving_pct"] > 60.0
    excluded = set(doc.get("excluded_lane_ids") or [])
    assert "ijeoma_chunk_table_v1" in excluded
    assert "ijeoma_chunk_cjk_hypo_v1" in excluded


def test_cjk_bridge_vs_eval_hook_parity():
    path = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_bridge_vs_eval_hook_v1.json"
    assert path.is_file()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["parity_ok"] is True
    assert doc["case_count"] == 90
    assert doc["compressed_text_mismatch_count"] == 0
