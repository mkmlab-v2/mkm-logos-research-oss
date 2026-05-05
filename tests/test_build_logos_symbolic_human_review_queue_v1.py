from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_symbolic_human_review_queue_v1.py"


def test_queue_opens_when_gate_is_go(tmp_path: Path):
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "logos_symbolic_event_promotion_gate_v1",
                "decision": "GO_RESEARCH_PROMOTION_CANDIDATE",
                "all_pass": True,
                "metrics_snapshot": {"n_evaluated": 99, "hit_rate": 0.6},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "queue.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--promotion-gate-json",
            str(gate),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("included") is True
    assert doc.get("status") == "open"
    assert len(doc.get("items") or []) == 1


def test_queue_closes_when_gate_is_human_approved(tmp_path: Path):
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "logos_symbolic_event_promotion_gate_v1",
                "decision": "GO_RESEARCH_PROMOTION_CANDIDATE_WITH_HUMAN_APPROVAL",
                "all_pass": True,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "queue.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--promotion-gate-json",
            str(gate),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("included") is False
    assert doc.get("status") == "closed"
    assert (doc.get("items") or []) == []

