# Purpose: commander human-review apply + posteval preserve contract.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_commander_apply_sets_human_gate(tmp_path: Path) -> None:
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "schema": "myeongri_interpret_v4_human_review_sample_v1",
                "samples": [{"row_index": 65}, {"row_index": 10}],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_myeongri_interpret_v4_commander_human_review_v1.py"),
            "--sample-json",
            str(sample),
            "--status-json",
            str(tmp_path / "missing_status.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(sample.read_text(encoding="utf-8"))
    assert doc["human_gate_pass"] is True
    assert doc["human_verdict_counts"]["pass"] == 2
    assert all(s["reviewer_verdict_source"] == "commander_v1" for s in doc["samples"])


def test_posteval_preserves_commander_fields(tmp_path: Path) -> None:
    from scripts.build_myeongri_interpret_v4_posteval_bundle_v1 import _commander_fields_from_prior

    p = tmp_path / "prior.json"
    p.write_text(
        json.dumps(
            {
                "commander_signed_at_utc": "2026-01-01T00:00:00Z",
                "human_gate_pass": True,
                "samples": [
                    {
                        "row_index": 10,
                        "reviewer_verdict": "pass",
                        "reviewer_verdict_source": "commander_v1",
                        "reviewer_comment": "ok",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    by_row, top = _commander_fields_from_prior(p)
    assert 10 in by_row
    assert by_row[10]["reviewer_comment"] == "ok"
    assert top.get("human_gate_pass") is True
