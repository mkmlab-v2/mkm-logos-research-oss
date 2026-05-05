# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_myeongri_ai_prompt_chain_v1 import _extract_json_object, validate_envelope_text


def test_extract_json_from_fenced_block() -> None:
    text = "prefix\n```json\n{\"schema\":\"myeongri_ai_interpretation_envelope_v1\"}\n```\nsuffix"
    obj = _extract_json_object(text)
    assert obj["schema"] == "myeongri_ai_interpretation_envelope_v1"


def test_validate_envelope_text_minimal() -> None:
    payload = {
        "schema": "myeongri_ai_interpretation_envelope_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mkm_advanced_insight": "[HYPO] deterministic payload aligned narrative.",
        "confidence_score": 0.5,
        "human_review_required": True,
        "prohibition_ack": "Not live trading, not medical, not doctrinal finality.",
    }
    text = json.dumps(payload, ensure_ascii=False)
    out = validate_envelope_text(text)
    assert out["schema"] == "myeongri_ai_interpretation_envelope_v1"


def test_chain_writes_prompt_and_recommendation(tmp_path: Path) -> None:
    from scripts.run_myeongri_ai_prompt_chain_v1 import main

    prompt_out = tmp_path / "prompt.txt"
    rec_out = tmp_path / "rec.json"

    import sys

    argv = [
        "run_myeongri_ai_prompt_chain_v1.py",
        "--profile",
        "daewoon",
        "--prompt-out",
        str(prompt_out),
        "--recommendation-out",
        str(rec_out),
        "--deterministic-json-inline",
        '{"demo": true}',
    ]
    old = sys.argv
    sys.argv = argv
    try:
        rc = main()
    finally:
        sys.argv = old
    assert rc == 0
    assert prompt_out.is_file()
    assert rec_out.is_file()
