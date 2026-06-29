from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts" / "probe_layer1_only_brier_bench_resolvers_v1.py"
COHORT = ROOT / "docs" / "final" / "artifacts" / "layer1_only_brier_bench_poc_v1_latest.json"


def _scripts_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "scripts")
    env.pop("FRED_API_KEY", None)
    return env


def test_live_probe_covers_automated_hooks(tmp_path: Path) -> None:
    out = tmp_path / "probe.json"
    proc = subprocess.run(
        [sys.executable, str(PROBE), "--live", "--output", str(out)],
        cwd=ROOT,
        env=_scripts_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["resolved_candidate_count"] == 0
    by_qid = {p["question_id"]: p for p in report["probes"]}
    assert by_qid["poc.oecd_foresight_pdf_headings_2027"]["probe_kind"] == "document_structure"
    assert by_qid["poc.oecd_foresight_pdf_headings_2027"]["status"] in (
        "holdout_pending",
        "probe_inconclusive",
    )
    assert by_qid["poc.ecb_mro_above_3_5_before_20261231"]["probe_kind"] == "official_statistics"
    assert by_qid["poc.us_unemployment_below_4pct_2026h2"]["status"] == "holdout_pending"
    assert by_qid["poc.us_unemployment_below_4pct_2026h2"]["probe_kind"] == "official_statistics"
    assert report.get("fred_api_key_configured") is True


def test_oecd_heading_interim_holdout(tmp_path: Path) -> None:
    code = """
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "scripts")
from layer1_only_brier_bench_resolver_hooks_v1 import probe_oecd_foresight_headings

cohort = json.loads(Path("docs/final/artifacts/layer1_only_brier_bench_poc_v1_latest.json").read_text(encoding="utf-8"))
row = next(r for r in cohort["forecasts"] if "oecd" in r["question_id"])
fake = "Chapter 1 Intro\\nChapter 2 Methods\\nChapter 3 Data\\nChapter 4 Cases\\nChapter 5 Outlook"
with patch("layer1_only_brier_bench_resolver_hooks_v1.http_get", return_value={"ok": True, "status": 200, "body": fake, "body_preview": fake}), patch(
    "layer1_only_brier_bench_resolver_hooks_v1.deadline_reached", return_value=False
):
    probe = probe_oecd_foresight_headings(row, live=True)
assert probe["status"] == "holdout_pending"
assert probe["interim"]["page_heading_like_count"] >= 5
print("ok")
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=_scripts_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_weekly_readiness_script() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "Verify-Layer1OnlyBrierBenchWeeklyTaskReadiness_v1.ps1"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
