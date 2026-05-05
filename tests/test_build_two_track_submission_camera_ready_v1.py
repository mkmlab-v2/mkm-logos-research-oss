from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_two_track_submission_camera_ready_v1(tmp_path: Path) -> None:
    repo = tmp_path
    artifacts = repo / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True)
    draft = {
        "recommended_title": "Test Title",
        "abstract_scaffold_en": {"problem": "p", "method": "m", "result": "r", "claim_boundary": "b"},
        "submission_gate_snapshot": {"bundle_ready": True, "ready_for_publication_claim": True},
        "public_safe_boundary": "x",
    }
    dp = artifacts / "two_track_submission_draft_latest.json"
    dp.write_text(json.dumps(draft), encoding="utf-8")
    out = artifacts / "cam.json"
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_two_track_submission_camera_ready_v1.py"),
            "--repo-root",
            str(repo),
            "--draft-json",
            str(dp),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "two_track_submission_camera_ready_v1"
    assert len(doc["expanded_abstract_en"]["paragraphs"]) >= 4
