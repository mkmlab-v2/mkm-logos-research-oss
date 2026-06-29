"""extend_manseryeok_session_jsonl_v1 smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_extend_session_jsonl_idempotent(tmp_path):
    from scripts.extend_manseryeok_session_jsonl_v1 import extend_session_jsonl

    my = tmp_path / "my.jsonl"
    sa = tmp_path / "sa.jsonl"
    my.write_text(
        json.dumps(
            {
                "eval_date": "2026-06-25",
                "mapping_target": "bull",
                "session_direction_score": 0.1,
                "hypothesis_tier": "B",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    sa.write_text(my.read_text(encoding="utf-8"), encoding="utf-8")

    doc1 = extend_session_jsonl(
        through_date="2026-06-26",
        myeongni_path=my,
        sasang_path=sa,
        calendar_mode="krx_weekdays",
    )
    assert doc1["n_appended_myeongni"] >= 1
    doc2 = extend_session_jsonl(
        through_date="2026-06-26",
        myeongni_path=my,
        sasang_path=sa,
        calendar_mode="krx_weekdays",
    )
    assert doc2.get("n_appended") == 0 or doc2.get("n_appended_myeongni") == 0
