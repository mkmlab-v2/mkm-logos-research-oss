# Keywords: magic_orb, four_slot, interpretive_trajectory, fact_lock

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
DIGEST = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
SHADOW = ROOT / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def test_assembler_job_four_slot() -> None:
    from magic_orb_four_slot_assembler_v1 import assemble_four_slot_response

    digest = json.loads(DIGEST.read_text(encoding="utf-8"))
    shadow = json.loads(SHADOW.read_text(encoding="utf-8"))
    four = assemble_four_slot_response(
        query="욥이 고난을 받은 이유",
        query_id="job_suffering_reason",
        router=None,
        shadow=shadow,
        digest=digest,
        rag=[
            {
                "source_id": "logos_subgraph_verse:Job.1.6",
                "snippet": "Job 1:6 snippet",
                "evidence_kind": "subgraph_verse",
            },
            {
                "source_id": "logos_subgraph:path:test",
                "snippet": "path note",
                "evidence_kind": "subgraph_path",
            },
        ],
    )
    assert four["schema_version"] == "four_slot_response_v1"
    assert len(four["slots"]["fact_locked"]["items"]) == 0
    assert four["slots"]["fact_locked"]["empty_reason"] == "verified_anchor=false"
    assert len(four["slots"]["corpus_bound"]["items"]) >= 1
    assert len(four["slots"]["imagination_path"]["items"]) >= 2
    assert len(four["slots"]["unknown_gap"]["items"]) >= 1
    assert four["enforcement"]["forbidden_badge"] == "Fact-Lock 100%"


def test_trajectory_from_digest() -> None:
    from magic_orb_four_slot_assembler_v1 import build_interpretive_trajectory

    digest = json.loads(DIGEST.read_text(encoding="utf-8"))
    entry = digest["panorama_entries"][0]
    traj = build_interpretive_trajectory(digest_entry=entry)
    assert traj["schema_version"] == "interpretive_trajectory_v1"
    assert len(traj["trajectories"]) >= 4
    assert traj["interaction"]["no_merge_to_single_answer"] is True


def test_build_magic_orb_payload_v12_embed() -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_comparative_theology_panorama_digest_v1.py"),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py"),
            "--query",
            "욥이 고난을 받은 이유",
            "--query-id",
            "job_suffering_reason",
            "--shadow-json",
            str(SHADOW),
            "--digest-json",
            str(DIGEST),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(INSIGHT.read_text(encoding="utf-8"))
    assert doc.get("version") == "1.2.0"
    assert "four_slot_response_v1" in doc
    assert "interpretive_trajectory_v1" in doc
    assert "pipeline_waveform_v1" in doc
    assert doc["four_slot_response_v1"]["enforcement"]["send_gate"] == "HOLD"
