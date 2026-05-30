"""Smoke: covenant-convergence filter + edge hypothesis SFT JSONL."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTER = ROOT / "scripts/filter_logos_review_queue_covenant_convergence_v1.py"
SFT = ROOT / "scripts/build_logos_edge_hypothesis_sft_jsonl_v1.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_covenant_filter_caps_ann_lite_primary(tmp_path: Path) -> None:
    filt = _load_module(FILTER, "filter_logos_review_queue_covenant_convergence_v1")
    queue = {
        "schema": "logos_candidate_edge_human_review_queue_v1",
        "items": [
            {
                "queue_rank": 1,
                "lane_id": "ann_lite",
                "priority": "primary",
                "src_node_id": "aramaic::Jer.31.31",
                "dst_node_id": "aramaic::Jer.31.33",
                "similarity": 0.95,
            },
            {
                "queue_rank": 2,
                "lane_id": "ann_lite",
                "priority": "primary",
                "src_node_id": "aramaic::Gen.1.1",
                "dst_node_id": "aramaic::Gen.1.2",
                "similarity": 0.99,
            },
            {
                "queue_rank": 3,
                "lane_id": "offline_4d_knn",
                "priority": "secondary_4d_only",
                "src_node_id": "aramaic::Jer.31.20",
                "dst_node_id": "aramaic::Rom.11.5",
                "similarity": 0.98,
            },
        ],
    }
    anchors = {"Jer.31.31", "Jer.31.33", "Rom.11.5"}
    doc = filt.build_filtered_queue(queue, anchors=anchors, max_items=15)
    assert doc["schema"] == "logos_review_queue_covenant_convergence_v1"
    assert doc["merge_to_canonical_allowed"] is False
    assert doc["stats"]["selected_count"] == 1
    assert doc["items"][0]["src_node_id"] == "aramaic::Jer.31.31"


def test_sft_builder_writes_instruction_rows(tmp_path: Path) -> None:
    sft_mod = _load_module(SFT, "build_logos_edge_hypothesis_sft_jsonl_v1")
    filtered = {
        "items": [
            {
                "queue_rank": 1,
                "lane_id": "ann_lite",
                "pair_key": "a|b",
                "src_node_id": "aramaic::Jer.31.31",
                "dst_node_id": "aramaic::Rom.11.5",
                "edge_type": "semantic_ann_lite_knn",
                "similarity": 0.94,
                "review_decision": None,
            }
        ]
    }
    rows = sft_mod.build_sft_rows(filtered)
    assert len(rows) == 1
    assert "[HYPO]" in rows[0]["output"]
    assert rows[0]["metadata"]["merge_to_canonical_allowed"] is False

    out_jsonl = tmp_path / "sft.jsonl"
    out_manifest = tmp_path / "manifest.json"
    filtered_path = tmp_path / "filtered.json"
    filtered_path.write_text(json.dumps(filtered), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(SFT),
            "--filtered-json",
            str(filtered_path),
            "--output-jsonl",
            str(out_jsonl),
            "--manifest-json",
            str(out_manifest),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    lines = out_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    manifest = json.loads(out_manifest.read_text(encoding="utf-8"))
    assert manifest["human_signoff_required"] is True


def test_microtrain_dry_run_contract(tmp_path: Path) -> None:
    jsonl = tmp_path / "sft.jsonl"
    row = {
        "instruction": "Logos edge [HYPO] test",
        "output": "[HYPO] guarded edge",
        "metadata": {"merge_to_canonical_allowed": False},
    }
    jsonl.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    report = tmp_path / "report.json"
    adapter = tmp_path / "adapter"
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_logos_edge_hypothesis_microtrain_v1.py"),
            "--jsonl",
            str(jsonl),
            "--adapter-out",
            str(adapter),
            "--report-json",
            str(report),
            "--mode",
            "dry_run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(report.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_edge_hypothesis_microtrain_v1"
    assert doc["microtrain_smoke_ok"] is True
    assert doc["kaggle_lane"] is False
