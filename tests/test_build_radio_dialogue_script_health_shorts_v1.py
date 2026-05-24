"""Health shorts builder."""

import json
from pathlib import Path

import scripts.build_radio_dialogue_script_health_shorts_v1 as health
import scripts.check_radio_dialogue_script_v1 as gate


def test_health_build_and_gate(tmp_path: Path) -> None:
    logos = {"golden_anchor": {"ref": "잠언 3:5", "text": "신뢰", "theme": "길"}}
    briefing = {
        "calendar_kst": "2026-05-22",
        "world_pulse": {"macro": {"risk_warning_level": "low"}},
        "hypothesis_stream": {"synthesis_ko": "페이싱", "branches": [{}]},
        "user_condition": {"stress_band": "mid"},
    }
    fortune = {"calendar_kst": "2026-05-22", "myeongni_lines": ["▸ 페이싱"]}
    weather = {"weather_band": "mild", "temp_c": 20}
    for name, doc in [
        ("logos.json", logos),
        ("briefing.json", briefing),
        ("fortune.json", fortune),
        ("weather.json", weather),
    ]:
        (tmp_path / name).write_text(json.dumps(doc), encoding="utf-8")

    doc = health.build_health_shorts_doc(
        tmp_path,
        logos_path=tmp_path / "logos.json",
        briefing_path=tmp_path / "briefing.json",
        fortune_path=tmp_path / "fortune.json",
        weather_path=tmp_path / "weather.json",
    )
    assert doc["program_skin"] == "tkm_health_24h"
    report = gate.check_radio_dialogue_script(doc)
    assert report["gate_ok"] is True
    assert report["program_skin"] == "tkm_health_24h"
