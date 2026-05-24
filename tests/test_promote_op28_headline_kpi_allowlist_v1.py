"""Evolution allowlist gate on promote_op28_headline_kpi_v1."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def test_headline_kpi_promotion_allowlist_ok() -> None:
    from evolution_auto_apply_allowlist_v1 import assert_headline_kpi_promotion_allowed
    from prophecy_hit_rate_ssot_v1 import HEADLINE_KPI

    assert_headline_kpi_promotion_allowed(
        min_confidence=0.18,
        score_abs_deadzone=0.0,
        output=HEADLINE_KPI,
    )


def test_promote_rejects_out_of_range_min_confidence() -> None:
    score = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    if not score.is_file():
        return
    out = ROOT / "reports" / "tmp_promote_allowlist_fail.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "promote_op28_headline_kpi_v1.py"),
            "--score-json",
            str(score),
            "--per-date-json",
            str(ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_v1_latest.json"),
            "--min-confidence",
            "1.5",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "allowlist" in (cp.stderr + cp.stdout).lower()
    if out.is_file():
        out.unlink()


def test_promote_rejects_non_headline_output_path() -> None:
    score = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    if not score.is_file():
        return
    out = ROOT / "reports" / "tmp_promote_wrong_output.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "promote_op28_headline_kpi_v1.py"),
            "--score-json",
            str(score),
            "--min-confidence",
            "0.18",
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "headline" in (cp.stderr + cp.stdout).lower() or "ssot" in (cp.stderr + cp.stdout).lower()


def test_promote_skip_allowlist_writes_tmp() -> None:
    score = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    per_date = ROOT / "reports" / "btrack_ensemble_per_date_directions_180d_v1_latest.json"
    if not score.is_file() or not per_date.is_file():
        return
    out = ROOT / "reports" / "tmp_promote_skip_allowlist.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "promote_op28_headline_kpi_v1.py"),
            "--score-json",
            str(score),
            "--per-date-json",
            str(per_date),
            "--min-confidence",
            "0.18",
            "--output",
            str(out),
            "--skip-evolution-allowlist",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_hit_rate_eval_report_v2"
    hp = doc.get("headline_promotion_v1") or {}
    assert hp.get("evolution_allowlist_v1", {}).get("checked") is False
    out.unlink()
