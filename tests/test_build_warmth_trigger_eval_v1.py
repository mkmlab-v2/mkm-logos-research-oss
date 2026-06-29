from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.build_warmth_trigger_eval_v1 import (
    build_eval_report,
    classify_epb_outcome,
    _apply_sasang_overlay,
    _load_json,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DOSE = ROOT / "docs/final/schemas/warmth_content_dose_v1.example.json"
OVERLAY = ROOT / "docs/final/artifacts/epb_sasang_overlay_rules_v1.json"
SESSION = ROOT / "docs/final/artifacts/fixtures/warmth_trigger_eval_session_v1.example.json"


def _profile() -> dict:
    return _load_json(PROFILE)


def test_classify_hit_on_fixture_session():
    profile = _profile()
    session = _load_json(SESSION)
    outcome, _ = classify_epb_outcome(
        pre_valence=session["pre"]["valence"],
        pre_arousal=session["pre"]["arousal"],
        post_valence=session["post"]["valence"],
        post_arousal=session["post"]["arousal"],
        profile=profile,
        pre_surprisal=session.get("pre_surprisal_0_1"),
        post_surprisal=session.get("post_surprisal_0_1"),
    )
    assert outcome == "hit"


def test_classify_over_on_valence_floor():
    profile = _profile()
    outcome, details = classify_epb_outcome(
        pre_valence=0.0,
        pre_arousal=0.0,
        post_valence=-0.55,
        post_arousal=0.1,
        profile=profile,
    )
    assert outcome == "over"
    assert details["reason"] == "t_high_breach"


def test_classify_hysteresis_cooldown_when_prior_overload():
    profile = _profile()
    outcome, details = classify_epb_outcome(
        pre_valence=-0.1,
        pre_arousal=0.0,
        post_valence=0.3,
        post_arousal=0.15,
        profile=profile,
        prior_overload=True,
    )
    assert outcome == "hysteresis_cooldown"
    assert "recovery" in details["reason"]


def test_soeumin_overlay_lowers_arousal_hi():
    profile = _profile()
    overlay = _load_json(OVERLAY)
    adjusted = _apply_sasang_overlay(profile, overlay)
    assert (
        adjusted["epb"]["sweet_band"]["arousal_hi"]
        < profile["epb"]["sweet_band"]["arousal_hi"]
    )


def test_build_eval_report_integration():
    report = build_eval_report(
        profile=_profile(),
        dose=_load_json(DOSE),
        session=_load_json(SESSION),
        overlay=_load_json(OVERLAY),
    )
    assert report["schema"] == "warmth_trigger_eval_v1"
    assert report["research_only"] is True
    assert report["outcome"] == "hit"
    assert report["overlay_applied"] is True


def test_cli_writes_latest_json(tmp_path: Path):
    out = tmp_path / "warmth_trigger_eval_test.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_warmth_trigger_eval_v1.py"),
        "--session-json",
        str(SESSION),
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["outcome"] == "hit"
