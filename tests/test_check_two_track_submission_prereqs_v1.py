from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")


def test_check_two_track_submission_prereqs_v1(tmp_path: Path) -> None:
    repo = tmp_path
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    chain = scripts / "run_aramaic_mvp_chain_v1.ps1"
    chain.write_text(
        'Write-Host "x"\n& py "scripts/a.py"\n& py "scripts/b.py"\n',
        encoding="utf-8",
    )
    (scripts / "a.py").write_text("print('ok')\n", encoding="utf-8")

    artifacts = repo / "docs" / "final" / "artifacts"
    _write_json(artifacts / "two_track_falsification_suite_latest.json", {"generated_at_utc": "2026-01-01T00:00:00Z"})
    _write_json(artifacts / "two_track_benchmark_comparison_latest.json", {"generated_at_utc": "2026-01-01T00:00:01Z"})
    _write_json(
        artifacts / "two_track_statistical_significance_report_latest.json",
        {"generated_at_utc": "2026-01-01T00:00:02Z"},
    )
    _write_json(artifacts / "two_track_raw_oos_readiness_latest.json", {"generated_at_utc": "2026-01-01T00:00:03Z"})
    # intentionally missing public_safe_report

    out = artifacts / "prereq.json"
    subprocess.run(
        [
            "py",
            str(ROOT / "scripts" / "check_two_track_submission_prereqs_v1.py"),
            "--repo-root",
            str(repo),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        check=True,
    )
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "two_track_submission_prereq_check_v1"
    assert doc["gates"]["required_artifacts_ready"] is False
    assert "public_safe_report" in doc["gates"]["missing_required_artifacts"]
    assert doc["chain_scan"]["missing_python_refs_count"] == 1

