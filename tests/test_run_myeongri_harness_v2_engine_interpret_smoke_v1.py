"""Harness v2 smoke: engine pillars + interpret instruction wiring."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict
from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import (
    _build_interpret_instruction,
    _canonical_json,
)
from scripts.myeongri_deterministic_lora_golden_views_v1 import pillars_view


def test_engine_recompute_matches_golden_first_locked_eval_row() -> None:
    golden_path = Path("data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl")
    line = golden_path.read_text(encoding="utf-8").splitlines()[0]
    row = json.loads(line)
    recomputed = build_golden_row_dict(
        str(row["birth_instant_utc"]),
        str(row["iana_tz"]),
        bool(row.get("is_male", False)),
        str(row["sample_id"]),
        "locked_eval",
    )["expected_result"]
    assert _canonical_json(pillars_view(recomputed)) == _canonical_json(
        pillars_view(row["expected_result"])
    )


def test_interpret_instruction_mentions_envelope_not_saju_compute() -> None:
    msg = _build_interpret_instruction(
        deterministic_payload={"schema": "saju_global_birth_result_v1", "full_saju": {"saju": {}}},
        lang="ko",
        sha256_hex="a" * 64,
    )
    assert "myeongri_ai_interpretation_envelope_v1" in msg
    assert "CRITICAL (Harness v2)" in msg
    assert "deterministic inputs only" in msg.lower()
