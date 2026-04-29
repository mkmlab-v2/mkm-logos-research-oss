from __future__ import annotations

import json
from pathlib import Path

from scripts import run_manseryeok_bot_v1 as mod


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_profile_json_local_input(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / "profile.json"
    out = tmp_path / "out.json"
    _write(
        profile,
        {
            "name": "ladakh_case",
            "sex": "female",
            "analysis_depth": "pro",
            "place": "ladakh",
            "local": {"year": 2021, "month": 1, "day": 5, "hour": 19, "minute": 0},
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_manseryeok_bot_v1.py",
            "--profile-json",
            str(profile),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "manseryeok_bot_v1"
    assert doc["profile"]["place"] == "ladakh"
    assert doc["profile"]["sex"] == "female"
    assert doc["profile"]["analysis_depth"] == "pro"
    assert doc["analysis"]["depth"] == "pro"
    assert "details" in doc["analysis"]
    assert "daewoon_text" in doc["analysis"]["details"]
    assert "yeonun_text" in doc["analysis"]["details"]
    assert "luck" in doc
    assert "daewoon" in doc["luck"]
    assert "alternative_hour_option" in doc
    assert doc["alternative_hour_option"]["enabled"] is True
    assert "review_interpretation" in doc
    assert "병행 검토" in doc["review_interpretation"]["paragraph_ko"]
    assert "primary_engine" in doc["pillars"]


def test_basic_depth_hides_luck_block(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / "profile_basic.json"
    out = tmp_path / "out_basic.json"
    _write(
        profile,
        {
            "name": "ladakh_case_basic",
            "sex": "female",
            "analysis_depth": "basic",
            "place": "ladakh",
            "local": {"year": 2021, "month": 1, "day": 5, "hour": 19, "minute": 0},
        },
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_manseryeok_bot_v1.py",
            "--profile-json",
            str(profile),
            "--out",
            str(out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["profile"]["analysis_depth"] == "basic"
    assert doc["analysis"]["depth"] == "basic"
    assert "luck" not in doc
    assert "alternative_hour_option" in doc
    assert "review_interpretation" in doc
