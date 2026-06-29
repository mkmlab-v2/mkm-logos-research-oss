# Purpose: MKM skill trigger heuristic eval + description A/B contract.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_skill_trigger_eval_strict_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/eval_mkm_skill_triggers_v1.py"), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(
        (ROOT / "docs/final/artifacts/skill_trigger_eval_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["ok"] is True
    assert doc["metrics"]["positive"]["recall"] >= doc["thresholds"]["min_recall"]
    assert doc["metrics"]["precision"] >= doc["thresholds"]["min_precision"]
    assert (
        doc["metrics"]["negative"]["cross_skill_false_positive_rate"]
        <= doc["thresholds"]["max_cross_skill_false_positive_rate"]
    )
    assert (
        doc["metrics"]["conflict"]["priority_accuracy"]
        >= doc["thresholds"].get("min_conflict_accuracy", 1.0)
    )
    skill_names = {row["name"] for row in doc["skills"]}
    assert "mkm-gut-brain-trackc-comms" in skill_names


def test_skill_trigger_ab_compare_passes() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/eval_mkm_skill_triggers_v1.py"),
            "--ab-only",
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(
        (ROOT / "docs/final/artifacts/skill_trigger_eval_ab_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["ok"] is True
    assert doc["control_beats_vague"] is True
    briefing_winner = doc["winners_by_skill"]["mkm-internal-standardized-briefing"]
    assert briefing_winner in ("briefing-control", "briefing-trigger-rich")
    assert doc["winners_by_skill"]["mkm-cursor-session-ops"] == "session-control"
    by_id = {row["variant_id"]: row for row in doc["variants"]}
    assert by_id["briefing-control"]["skill_recall"] == 1.0
    assert by_id["briefing-vague"]["skill_recall"] < by_id["briefing-control"]["skill_recall"]
    assert by_id["session-vague"]["skill_recall"] < by_id["session-control"]["skill_recall"]
