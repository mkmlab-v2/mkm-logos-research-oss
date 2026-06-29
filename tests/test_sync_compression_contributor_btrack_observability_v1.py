"""B-track observability sync for contributor bridge."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts/sync_compression_contributor_btrack_observability_v1.py"


def test_build_bundle_and_agent_log(tmp_path: Path) -> None:
    signoff = tmp_path / "signoff.json"
    signoff.write_text(
        json.dumps(
            {
                "tenant_id": "t1",
                "candidate_path": "cand.json",
                "contributor_jsonl": "data/x.jsonl",
                "validate_sha256": "abc",
                "metrics_at_apply": {"pass_rate": 1.0},
                "promotion_gates_at_apply": {"validation_ok": True},
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "latest_signoff": str(signoff.name),
                "candidate_snapshot": {"path": "cand.json"},
            }
        ),
        encoding="utf-8",
    )
    cand = tmp_path / "cand.json"
    cand.write_text(
        json.dumps({"rehearsal_only": True, "tenant_id": "t1", "metrics": {"rows": 12}}),
        encoding="utf-8",
    )
    bundle = tmp_path / "bundle.json"
    log_path = tmp_path / "agent.jsonl"

    proc = subprocess.run(
        [
            sys.executable,
            str(SYNC),
            "--signoff-json",
            str(signoff),
            "--evidence-json",
            str(evidence),
            "--candidate-json",
            str(cand),
            "--bundle-out",
            str(bundle),
            "--skip-agent-log",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(bundle.read_text(encoding="utf-8"))
    assert doc["btrack_learning_material"] is True
    assert doc["rehearsal_only"] is True
    assert doc["auto_track_a_promotion_allowed"] is False
