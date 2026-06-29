# Keywords: question_semantic_rag_bridge, magic_orb, chain, four_slot

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
CHAIN = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"


def test_bridge_chain_job_query_exit_zero() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            "욥이 고난을 받은 이유",
            "--query-id",
            "job_suffering_reason",
            "--skip-ann-lite",
            "--sync-public",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stderr + r.stdout

    chain = json.loads(CHAIN.read_text(encoding="utf-8"))
    assert chain.get("schema") == "question_semantic_rag_bridge_chain_v1"
    steps = chain.get("steps") or {}
    assert steps.get("panorama_preflight", {}).get("ok") is True
    assert steps.get("four_slot_validate", {}).get("ok") is True

    doc = json.loads(INSIGHT.read_text(encoding="utf-8"))
    assert doc.get("version") == "1.2.0"
    assert "four_slot_response_v1" in doc
    assert doc["four_slot_response_v1"]["enforcement"]["send_gate"] == "HOLD"


def test_bridge_chain_dry_run() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            "욥이 고난을 받은 이유",
            "--query-id",
            "job_suffering_reason",
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "[dry-run]" in r.stdout
