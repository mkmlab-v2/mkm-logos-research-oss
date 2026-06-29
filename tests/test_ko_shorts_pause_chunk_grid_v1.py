"""Offline tests for ko shorts pause chunk grid [HYPO]."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_ko_shorts_pause_chunk_grid_v1 import build_pause_chunk_grid_v1  # noqa: E402


def test_pause_chunk_grid_fixture_has_recommendation() -> None:
    report = build_pause_chunk_grid_v1(
        cases=[{"case_id": "fixture", "wav": "fixture"}],
        pause_gaps=(0.3, 0.4),
        max_chars_list=(16, 28),
        profile_key="netflix_v16",
        from_fixture=True,
    )
    assert report["schema"] == "ko_shorts_pause_chunk_grid_v1"
    cases = report.get("cases") or []
    assert len(cases) == 1
    assert cases[0]["ok"] is True
    assert cases[0]["recommendation"]["pause_gap_sec"] in (0.3, 0.4)
    assert cases[0]["recommendation"]["max_chars"] in (16, 28)


def test_pause_chunk_grid_json_roundtrip() -> None:
    report = build_pause_chunk_grid_v1(
        cases=[{"case_id": "fixture", "wav": "fixture"}],
        pause_gaps=(0.4,),
        max_chars_list=(28,),
        profile_key="netflix_v16",
        from_fixture=True,
    )
    blob = json.dumps(report, ensure_ascii=False)
    parsed = json.loads(blob)
    assert parsed["consensus_recommendation"]["max_chars"] == 28
