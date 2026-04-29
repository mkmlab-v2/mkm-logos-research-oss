# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.7, K:0.3, M:0.6}
# Balance: 86
# Purpose: Smoke test for real survivor resonance daily builder.
# Keywords: pytest, real, resonance, w3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_global_atom_survivor_resonance_daily_real_v1.py"


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_real_survivor_resonance_daily_jsonl(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    w3 = tmp_path / "w3.json"
    sidecar = tmp_path / "sidecar.json"
    mapping = tmp_path / "mapping.json"
    out_jsonl = tmp_path / "real.jsonl"

    _write_json(knowledge, {"summary": {"survivor_count": 1}, "survivor_ids": ["cand_001"]})
    _write_json(candidates, {"candidates": [{"candidate_id": "cand_001", "source_node_id": "x", "hub_score": 0.9}]})
    _write_json(w3, {"top_n_results": [{"resonance_score": 0.8}, {"resonance_score": 0.6}]})
    _write_json(sidecar, {"per_date_features": [{"eval_date": "2020-01-01", "instrument": "kospi", "myeongni_insight_lines_cumulative_through_eval_date": 2}]})
    _write_json(mapping, {"schema": "global_atom_survivor_w3_direct_mapping_v1", "rows": []})

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--w3-result-json",
            str(w3),
            "--sidecar-json",
            str(sidecar),
            "--mapping-json",
            str(mapping),
            "--output-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["signal_mode"] == "real_from_w3_batch_topn_v1"
    assert row["mapping_quality"] == "weak_mapping"


def test_build_real_survivor_resonance_daily_jsonl_with_direct_mapping(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    w3 = tmp_path / "w3.json"
    sidecar = tmp_path / "sidecar.json"
    mapping = tmp_path / "mapping.json"
    out_jsonl = tmp_path / "real_direct.jsonl"

    _write_json(knowledge, {"summary": {"survivor_count": 1}, "survivor_ids": ["cand_001"]})
    _write_json(candidates, {"candidates": [{"candidate_id": "cand_001", "source_node_id": "x", "hub_score": 0.9}]})
    _write_json(w3, {"top_n_results": [{"sample_id": "S1", "resonance_score": 0.82}]})
    _write_json(sidecar, {"per_date_features": [{"eval_date": "2020-01-01", "instrument": "kospi", "myeongni_insight_lines_cumulative_through_eval_date": 2}]})
    _write_json(mapping, {"schema": "global_atom_survivor_w3_direct_mapping_v1", "rows": [{"candidate_id": "cand_001", "assigned_sample_ids": ["S1"]}]})

    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--w3-result-json",
            str(w3),
            "--sidecar-json",
            str(sidecar),
            "--mapping-json",
            str(mapping),
            "--output-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [ln for ln in out_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["mapping_quality"] == "direct_mapping_seeded_v1"
    assert row["components"]["mapped_sample_ids"] == ["S1"]


def test_build_real_survivor_resonance_daily_jsonl_regime_adaptive_mode(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    w3 = tmp_path / "w3.json"
    sidecar = tmp_path / "sidecar.json"
    mapping = tmp_path / "mapping.json"
    out_jsonl = tmp_path / "real_adaptive.jsonl"

    _write_json(knowledge, {"summary": {"survivor_count": 1}, "survivor_ids": ["cand_001"]})
    _write_json(candidates, {"candidates": [{"candidate_id": "cand_001", "source_node_id": "x", "hub_score": 0.9}]})
    _write_json(w3, {"top_n_results": [{"sample_id": "S1", "resonance_score": 0.82}]})
    _write_json(
        sidecar,
        {
            "per_date_features": [
                {
                    "eval_date": "2020-01-01",
                    "instrument": "kospi",
                    "myeongni_insight_lines_cumulative_through_eval_date": 2,
                    "score_row_context": {"flow_score_for_reversal": 9000},
                }
            ]
        },
    )
    _write_json(mapping, {"schema": "global_atom_survivor_w3_direct_mapping_v1", "rows": [{"candidate_id": "cand_001", "assigned_sample_ids": ["S1"]}]})
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--w3-result-json",
            str(w3),
            "--sidecar-json",
            str(sidecar),
            "--mapping-json",
            str(mapping),
            "--regime-adaptive-weighting",
            "--output-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    row = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[0])
    eff = row["components"]["effective_weights"]
    assert eff["mode"] == "regime_adaptive_v1"
    assert eff["regime_bucket"] in {"high_volatility", "mid_volatility", "low_volatility"}


def test_build_real_survivor_resonance_daily_jsonl_market_shock_weight(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge.json"
    candidates = tmp_path / "candidates.json"
    w3 = tmp_path / "w3.json"
    sidecar = tmp_path / "sidecar.json"
    mapping = tmp_path / "mapping.json"
    out_jsonl = tmp_path / "real_shock.jsonl"

    _write_json(knowledge, {"summary": {"survivor_count": 1}, "survivor_ids": ["cand_001"]})
    _write_json(candidates, {"candidates": [{"candidate_id": "cand_001", "source_node_id": "x", "hub_score": 0.9}]})
    _write_json(w3, {"top_n_results": [{"sample_id": "S1", "resonance_score": 0.82}]})
    _write_json(
        sidecar,
        {
            "per_date_features": [
                {
                    "eval_date": "2020-01-01",
                    "instrument": "kospi",
                    "myeongni_insight_lines_cumulative_through_eval_date": 2,
                    "score_row_context": {"daily_return": -0.03, "flow_score_for_reversal": 0.0},
                }
            ]
        },
    )
    _write_json(mapping, {"schema": "global_atom_survivor_w3_direct_mapping_v1", "rows": [{"candidate_id": "cand_001", "assigned_sample_ids": ["S1"]}]})
    proc = subprocess.run(
        [
            "py",
            str(SCRIPT),
            "--knowledge-report-json",
            str(knowledge),
            "--candidates-json",
            str(candidates),
            "--w3-result-json",
            str(w3),
            "--sidecar-json",
            str(sidecar),
            "--mapping-json",
            str(mapping),
            "--w-market-shock",
            "0.2",
            "--output-jsonl",
            str(out_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    row = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[0])
    eff = row["components"]["effective_weights"]
    assert eff["w_market_shock"] == 0.2
    assert row["components"]["market_shock_unit_from_abs_daily_return"] > 0.0

