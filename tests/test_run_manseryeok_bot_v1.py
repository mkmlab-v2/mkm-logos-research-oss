from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from scripts import run_manseryeok_bot_v1 as mod

from myeongni_lens_v1.fusion_bridge import unwrap_fusion_payload


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
    assert "daewoon_qiyun_v1" in doc["luck"]
    assert "myeongri_fusion_v1" in doc["luck"]
    assert doc["luck"]["myeongri_fusion_v1"]["vector_4d_rule_school_v1"]
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


def test_basic_depth_writes_complete_fusion_sidecar(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / "profile_basic_fusion.json"
    out = tmp_path / "out_basic_fusion.json"
    fusion_out = tmp_path / "complete_fusion.json"
    _write(
        profile,
        {
            "name": "fusion_dump_case",
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
            "--write-complete-fusion-json",
            str(fusion_out),
        ],
    )
    assert mod.main() == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["profile"]["analysis_depth"] == "basic"
    assert "luck" not in doc
    fus_doc = json.loads(fusion_out.read_text(encoding="utf-8"))
    assert isinstance(fus_doc.get("saju"), dict)
    assert isinstance(fus_doc.get("daewoon_v1"), list)
    assert fus_doc.get("jijangan_v1", {}).get("schema") == "jijangan_overlay_v1"
    assert unwrap_fusion_payload(fus_doc) is not None
