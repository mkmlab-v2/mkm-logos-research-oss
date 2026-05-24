from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_family_anchor_lived_fact_check_v1.py"
FIXTURE_SESSION = ROOT / "tests" / "fixtures" / "family_anchor_fact_check_session_daughter_sample_v1.json"
FIXTURE_ANCHOR = ROOT / "tests" / "fixtures" / "family_anchor_lived_calibration_daughter_apply_fixture_v1.json"


def _write_fixture_anchor() -> None:
    src = ROOT / "docs/final/artifacts/family_anchor_lived_calibration_our_daughter_v1_latest.json"
    FIXTURE_ANCHOR.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_ANCHOR.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def test_apply_family_anchor_lived_fact_check_merges_responses(tmp_path: Path) -> None:
    _write_fixture_anchor()
    anchor_copy = tmp_path / "anchor.json"
    session_copy = tmp_path / "session.json"
    report = tmp_path / "report.json"
    anchor_copy.write_text(FIXTURE_ANCHOR.read_text(encoding="utf-8"), encoding="utf-8")
    session_copy.write_text(FIXTURE_SESSION.read_text(encoding="utf-8"), encoding="utf-8")

    v4_copy = tmp_path / "v4.json"
    v4_src = ROOT / "docs/final/artifacts/daughter_2026_integrated_guide_v4_minimal_latest.json"
    v4_copy.write_text(v4_src.read_text(encoding="utf-8"), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--session-json",
            str(session_copy),
            "--anchor-json",
            str(anchor_copy),
            "--v4-json",
            str(v4_copy),
            "--report-json",
            str(report),
        ],
        cwd=ROOT,
        check=True,
    )

    anchor = json.loads(anchor_copy.read_text(encoding="utf-8"))
    wealth = next(x for x in anchor["supplementary_axes"] if x["axis"] == "wealth_pocket_money")
    assert wealth["responses"]["pocket_money_comparison_stress"] == "neutral"
    assert wealth["responses"]["lived_check_status"] == "completed"
    assert "wealth_comparison_stress_lived_neutral" in anchor["preferred_narrative"]
    assert report.is_file()


def test_apply_rejects_incomplete_session(tmp_path: Path) -> None:
    _write_fixture_anchor()
    anchor_copy = tmp_path / "anchor.json"
    session_copy = tmp_path / "session.json"
    anchor_copy.write_text(FIXTURE_ANCHOR.read_text(encoding="utf-8"), encoding="utf-8")
    session_copy.write_text(FIXTURE_SESSION.read_text(encoding="utf-8"), encoding="utf-8")
    sess = json.loads(session_copy.read_text(encoding="utf-8"))
    sess["axes"][0]["responses"]["pocket_money_comparison_stress"] = None
    session_copy.write_text(json.dumps(sess), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--session-json",
            str(session_copy),
            "--anchor-json",
            str(anchor_copy),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "incomplete" in (proc.stderr + proc.stdout).lower()
