from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_two_track_submission_draft_v1(tmp_path: Path) -> None:
    repo = tmp_path
    artifacts = repo / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True)
    for fn, doc in (
        ("two_track_submission_evidence_bundle_latest.json", {"gates": {"bundle_ready": True, "missing_artifacts": []}}),
        ("two_track_raw_oos_readiness_latest.json", {"summary": {"ready_for_publication_claim": True}}),
        ("two_track_statistical_significance_report_latest.json", {"significance_interpretation": "ok"}),
        ("two_track_benchmark_comparison_latest.json", {"delta": {"shift_score": 0.1}}),
        ("two_track_public_safe_report_latest.json", {"public_safe": True}),
    ):
        (artifacts / fn).write_text(json.dumps(doc), encoding="utf-8")
    out = artifacts / "draft.json"
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_two_track_submission_draft_v1.py"),
            "--repo-root",
            str(repo),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["schema"] == "two_track_submission_draft_v1"
    assert "recommended_title" in d
