# Keywords: by_query, job_suffering, four_slot

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOB_HASH = "dc73c2c367199e48"
JOB_PUBLIC = ROOT / f"projects/mkm/mkm-life/public/data/magic_orb_insight_by_query/{JOB_HASH}.json"


def test_job_by_query_hash_stable() -> None:
    q = "욥이 고난을 받은 이유"
    norm = " ".join(q.strip().split())[:800]
    h = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]
    assert h == JOB_HASH


def test_chain_syncs_job_by_query_public() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            "욥이 고난을 받은 이유",
            "--query-id",
            "job_suffering_reason",
            "--skip-ann-lite",
            "--expand-graph",
            "--sync-public",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert JOB_PUBLIC.is_file()
    doc = json.loads(JOB_PUBLIC.read_text(encoding="utf-8"))
    assert doc.get("query_id") == "job_suffering_reason"
    assert "four_slot_response_v1" in doc
