from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_two_track_recovery_priority_v1(tmp_path: Path) -> None:
    repo = tmp_path
    artifacts = repo / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True)
    prereq = artifacts / "two_track_submission_prereq_check_latest.json"
    prereq.write_text(
        json.dumps(
            {
                "chain_scan": {
                    "missing_python_refs": [
                        {"script": "scripts/a.py", "exists": False},
                        {"script": "scripts/b.py", "exists": False},
                        {"script": "scripts/c.py", "exists": False},
                    ]
                },
                "gates": {"missing_required_artifacts": ["x", "y"]},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    out = artifacts / "priority.json"
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_two_track_recovery_priority_v1.py"),
            "--repo-root",
            str(repo),
            "--prereq-check-json",
            str(prereq),
            "--out",
            str(out),
            "--top-n",
            "2",
        ],
        cwd=str(ROOT),
        check=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "two_track_recovery_priority_v1"
    assert doc["summary"]["missing_python_refs_count"] == 3
    assert doc["summary"]["top_n"] == 2
    assert len(doc["top_priority_scripts"]) == 2
    assert doc["top_priority_scripts"][0]["script"] == "scripts/a.py"

