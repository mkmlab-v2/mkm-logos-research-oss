# Purpose: MKM live skill spot-check build + score contract.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUB_RESULTS = ROOT / "docs/final/artifacts/skill_live_spotcheck_stub_results.json"


def test_build_live_spotcheck_template() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_skill_live_spotcheck_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(
        (
            ROOT / "docs/final/artifacts/skill_live_spotcheck_template_latest.json"
        ).read_text(encoding="utf-8")
    )
    assert len(doc["rows"]) == 12
    assert doc["rows"][0]["pass"] is None


def test_score_live_spotcheck_stub_passes_thresholds() -> None:
    build = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_skill_live_spotcheck_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    template = json.loads(
        (
            ROOT / "docs/final/artifacts/skill_live_spotcheck_template_latest.json"
        ).read_text(encoding="utf-8")
    )
    template["run_provenance"] = "stub"
    for row in template["rows"]:
        row["run_provenance"] = "stub"
        row["chat_session"] = "pytest-stub"
        if row["kind"] in ("positive", "conflict"):
            row["observed_skill"] = row["expected_skill"]
            row["pass"] = True
        else:
            row["observed_skill"] = "none"
            row["pass"] = True
    STUB_RESULTS.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/score_mkm_skill_live_spotcheck_v1.py"),
            "--strict",
            "--allow-stub",
            "--input-json",
            "docs/final/artifacts/skill_live_spotcheck_stub_results.json",
            "--output-json",
            "docs/final/artifacts/skill_live_spotcheck_stub_score.json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    score = json.loads(
        (ROOT / "docs/final/artifacts/skill_live_spotcheck_stub_score.json").read_text(
            encoding="utf-8"
        )
    )
    assert score["ok"] is True
    assert score["metrics"]["positive"]["live_recall"] == 1.0


def test_auto_spotcheck_fills_and_scores() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_mkm_skill_live_spotcheck_auto_v1.py"),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    results = json.loads(
        (ROOT / "docs/final/artifacts/skill_live_spotcheck_results_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert results["run_provenance"] == "heuristic_auto"
    assert all(row["pass"] is not None for row in results["rows"])
    score = json.loads(
        (ROOT / "docs/final/artifacts/skill_live_spotcheck_score_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert score["provenance"] == "heuristic_auto"
    assert score["ok"] is True


def test_score_rejects_stub_results_latest_without_allow_stub() -> None:
    live_results = ROOT / "docs/final/artifacts/skill_live_spotcheck_results_latest.json"
    if not live_results.is_file():
        return
    doc = json.loads(live_results.read_text(encoding="utf-8"))
    if doc.get("run_provenance") == "live":
        return
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/score_mkm_skill_live_spotcheck_v1.py"),
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "provenance_not_allowed" in proc.stdout + proc.stderr
