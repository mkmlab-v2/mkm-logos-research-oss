from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import jsonschema

from scripts.scan_warmth_trigger_text_overload_v1 import scan_text, _load_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/warmth_trigger_text_overload_scan_v1.schema.json"
LEXICON = ROOT / "docs/final/artifacts/warmth_trigger_text_overload_lexicon_v1.json"
PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"


def _validate(report: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)


def test_calm_text_low_risk():
    report = scan_text(
        text="오늘은 조용히 쉬면서 천천히 숨 고를게. 괜찮아.",
        lexicon=_load_json(LEXICON),
        profile=_load_json(PROFILE),
    )
    _validate(report)
    assert report["overload_risk"] == "low"
    assert report["suggested_arm"] == "standard"
    assert report["t_high_breach_proxy"] is False


def test_despair_medium_or_high_suggests_cooldown_or_redose():
    report = scan_text(
        text="요즘 너무 절망적이고 무너진 것 같아. 포기하고 싶어.",
        lexicon=_load_json(LEXICON),
        profile=_load_json(PROFILE),
    )
    _validate(report)
    assert report["overload_risk"] in ("medium", "high")
    assert report["suggested_arm"] in ("re_dose_or_lower_intensity", "warm_only_cooldown")


def test_crisis_token_human_gate_hold():
    report = scan_text(
        text="너무 힘들어서 죽고 싶다는 생각이 들어.",
        lexicon=_load_json(LEXICON),
        profile=_load_json(PROFILE),
    )
    _validate(report)
    assert report["overload_risk"] == "human_gate_hold"
    assert report["suggested_arm"] == "human_gate_hold"
    assert any(m["signal_id"] == "crisis_self_harm_hint" for m in report["matched_signals"])


def test_compound_distress_can_breach_t_high_or_high_overload():
    report = scan_text(
        text="화나고 불안해. 초조하고 절망적이야. 미치겠어.",
        lexicon=_load_json(LEXICON),
        profile=_load_json(PROFILE),
    )
    _validate(report)
    assert report["overload_risk"] in ("medium", "high")
    assert report["suggested_arm"] in ("re_dose_or_lower_intensity", "warm_only_cooldown")
    assert len(report["matched_signals"]) >= 2


def test_cli_exit_zero():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/scan_warmth_trigger_text_overload_v1.py"),
            "--text",
            "괜찮아, 함께 힘내자.",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
