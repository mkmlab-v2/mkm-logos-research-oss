"""Smoke: promotion gate + ann_lite candidate builder."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_logos_candidate_edge_promotion_gate_v1.py"
PROMOTE = ROOT / "scripts/promote_logos_candidate_edge_survivors_v1.py"
ANN = ROOT / "scripts/build_logos_candidate_edges_from_ann_lite_v1.py"
SIGNOFF = ROOT / "docs/final/fixtures/logos_candidate_edge_promotion_signoff_v1.example.json"


def _sample_survivors(count: int = 2) -> dict:
    rows = []
    for i in range(count):
        rows.append(
            {
                "schema": "bible_meaning_graph_edge_candidate_v1",
                "src_node_id": f"aramaic::A.{i}",
                "dst_node_id": f"aramaic::B.{i}",
                "edge_type": "semantic_4d_knn",
                "edge_status": "candidate",
                "weight": 0.97,
                "similarity_4d_cosine": 0.97,
                "research_only": True,
                "promotion_required": True,
                "source_track": "B",
                "relation_basis": ["offline_4d_knn"],
            }
        )
    return {
        "schema": "logos_candidate_edge_survivors_v1",
        "stats": {"survivor_count": count},
        "survivors": rows,
        "merge_to_canonical_allowed": False,
    }


def test_promotion_gate_holds_without_signoff(tmp_path: Path) -> None:
    surv = tmp_path / "survivors.json"
    qual = tmp_path / "quality.json"
    out = tmp_path / "gate.json"
    surv.write_text(json.dumps(_sample_survivors(), ensure_ascii=False, indent=2), encoding="utf-8")
    qual.write_text(
        json.dumps(
            {
                "schema": "logos_candidate_edges_quality_v1",
                "saturation_warning": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--survivors-json",
            str(surv),
            "--quality-json",
            str(qual),
            "--signoff-json",
            str(SIGNOFF),
            "--output-json",
            str(out),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["gate_pass"] is False
    assert doc["status"] == "HOLD"


def test_promotion_gate_passes_with_approved_signoff(tmp_path: Path) -> None:
    surv = tmp_path / "survivors.json"
    qual = tmp_path / "quality.json"
    signoff = tmp_path / "signoff.json"
    gate_out = tmp_path / "gate.json"
    surv.write_text(json.dumps(_sample_survivors(), ensure_ascii=False, indent=2), encoding="utf-8")
    qual.write_text(
        json.dumps({"schema": "logos_candidate_edges_quality_v1", "saturation_warning": False}, ensure_ascii=False),
        encoding="utf-8",
    )
    signoff.write_text(
        json.dumps(
            {
                "schema": "logos_candidate_edge_promotion_signoff_v1",
                "approved": True,
                "expires_at_utc": "2099-01-01T00:00:00Z",
                "saturation_warning_acknowledged": True,
                "lora_prune_pending_acknowledged": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--survivors-json",
            str(surv),
            "--quality-json",
            str(qual),
            "--signoff-json",
            str(signoff),
            "--output-json",
            str(gate_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    gate = json.loads(gate_out.read_text(encoding="utf-8"))
    assert gate["gate_pass"] is True

    pending = tmp_path / "pending.jsonl"
    promo_out = tmp_path / "promo.json"
    proc2 = subprocess.run(
        [
            sys.executable,
            str(PROMOTE),
            "--gate-json",
            str(gate_out),
            "--survivors-json",
            str(surv),
            "--pending-jsonl-out",
            str(pending),
            "--output-json",
            str(promo_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc2.returncode == 0, proc2.stderr
    assert pending.is_file()
    assert sum(1 for _ in pending.read_text(encoding="utf-8").splitlines() if _.strip()) == 2


def test_ann_lite_builder_dry_run_or_build() -> None:
    sqlite = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"
    if not sqlite.is_file():
        proc = subprocess.run(
            [sys.executable, str(ANN), "--dry-run", "--max-query-verses", "10"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 2
        return

    proc = subprocess.run(
        [
            sys.executable,
            str(ANN),
            "--max-query-verses",
            "50",
            "--top-k",
            "2",
            "--min-cosine",
            "0.4",
            "--max-candidates",
            "80",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    summary = json.loads(
        (ROOT / "docs/final/artifacts/logos_candidate_edges_ann_lite_v1_latest.json").read_text(encoding="utf-8")
    )
    assert summary["schema"] == "logos_candidate_edges_ann_lite_v1"
    assert summary["stats"]["candidate_edges_written"] >= 1
