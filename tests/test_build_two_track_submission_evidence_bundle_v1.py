from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_two_track_submission_evidence_bundle_v1(tmp_path: Path) -> None:
    repo = tmp_path
    artifacts = repo / "docs" / "final" / "artifacts"
    artifacts.mkdir(parents=True)
    for name in (
        "two_track_falsification_suite_latest.json",
        "two_track_benchmark_comparison_latest.json",
        "two_track_statistical_significance_report_latest.json",
        "two_track_public_safe_report_latest.json",
    ):
        (artifacts / name).write_text(json.dumps({"generated_at_utc": "2026-01-01T00:00:00Z"}), encoding="utf-8")
    (artifacts / "two_track_raw_oos_readiness_latest.json").write_text(
        json.dumps({"generated_at_utc": "2026-01-01T00:00:00Z", "summary": {"ready_for_publication_claim": True}}),
        encoding="utf-8",
    )
    out = artifacts / "bundle.json"
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "build_two_track_submission_evidence_bundle_v1.py"),
            "--repo-root",
            str(repo),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "two_track_submission_evidence_bundle_v1"
    assert doc["gates"]["bundle_ready"] is True
