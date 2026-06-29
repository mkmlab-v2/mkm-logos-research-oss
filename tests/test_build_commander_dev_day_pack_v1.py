"""commander_dev_day_pack_v1 — B-track developer coaching bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_commander_dev_day_pack_v1 import build_pack  # noqa: E402

MAP = ROOT / "docs" / "final" / "artifacts" / "commander_dev_pack_pet_bridge_field_map_v1.json"
EX_PROFILE = ROOT / "docs" / "final" / "artifacts" / "commander_profile_v1.example.json"


def test_field_map_has_ten_rows_and_target():
    doc = json.loads(MAP.read_text(encoding="utf-8"))
    assert doc["schema"] == "commander_dev_pack_pet_bridge_field_map_v1"
    mappings = doc["mappings"]
    assert len(mappings) == 10
    subjects = [m.get("pet_subject_placeholder") for m in mappings]
    assert "[TARGET]" in subjects
    row6 = next(m for m in mappings if m["row"] == 6)
    assert row6["transform"] == "must_not_merge"


def test_build_pack_schema_and_firewall():
    fortune = {
        "schema": "commander_daily_fortune_v1",
        "as_of_date": "2026-06-05",
        "blocks": [{"id": "myeongni", "lines": ["▸ 오늘 한 줄: 검증 우선"]}],
        "user_condition": {"low_sleep": True},
    }
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "fortune.json"
        fp.write_text(json.dumps(fortune, ensure_ascii=False), encoding="utf-8")
        pack = build_pack(fortune_path=fp, profile_path=EX_PROFILE, workspace=ROOT)
    assert pack["schema"] == "commander_dev_day_pack_v1"
    assert pack["research_only"] is True
    assert pack["not_promoted_track_a"] is True
    assert pack["pack_meta"]["profile_id"] == "commander-dev"
    lines = pack.get("telegram_dev_coach_lines") or []
    text = "\n".join(lines)
    assert "개발 코치" in text
    assert "pet" in text.lower() or "[TARGET]" in text
    four = pack.get("four_ai_roles_for_dev") or {}
    assert "taeyang" in four
    assert "≠" in text or "분리" in text
