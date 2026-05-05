# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from scripts.build_myeongri_answer_draft_v1 import main


def test_build_answer_draft(tmp_path: Path) -> None:
    template_pack = tmp_path / "templates.json"
    recommendation = tmp_path / "recommendation.json"
    deterministic = tmp_path / "deterministic.json"
    out_json = tmp_path / "draft.json"
    out_md = tmp_path / "draft.md"

    template_pack.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "profile": "daewoon",
                        "lang": "ko",
                        "template": "profile={profile} fields={deterministic_fields} hypo={hypothesis_block}",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    recommendation.write_text(
        json.dumps(
            {
                "recommendations": [{"title": "X"}],
                "rag_sources_used_suggested": ["u1"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    deterministic.write_text(json.dumps({"state_id": 3}, ensure_ascii=False), encoding="utf-8")

    import sys

    argv = [
        "build_myeongri_answer_draft_v1.py",
        "--profile",
        "daewoon",
        "--lang",
        "ko",
        "--template-pack",
        str(template_pack),
        "--recommendation",
        str(recommendation),
        "--deterministic-json",
        str(deterministic),
        "--out-json",
        str(out_json),
        "--out-md",
        str(out_md),
    ]
    old = sys.argv
    sys.argv = argv
    try:
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    assert out_json.is_file()
    assert out_md.is_file()
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["schema"] == "myeongri_answer_draft_v1"
