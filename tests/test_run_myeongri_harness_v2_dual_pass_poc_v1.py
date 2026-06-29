"""Dual-pass harness v2 PoC (B-track, research_only)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.myeongri_interpret_envelope_views_v1 import (
    build_harness_v2_format_wrap_instruction,
    build_harness_v2_insight_only_instruction,
    dual_pass_deterministic_format_v1,
    normalize_hypo_tag_prefix,
    sha256_canonical,
    validate_envelope_required_fields,
)
from scripts.run_myeongri_harness_v2_dual_pass_poc_v1 import _normalize_pass1_prose
from scripts.myeongri_deterministic_lora_golden_views_v1 import compact_expected_result
from scripts.prep_myeongri_deterministic_lora_golden_v1 import build_golden_row_dict
from scripts.run_myeongri_harness_v2_dual_pass_poc_v1 import _pass1_insight_dry_run


def test_normalize_pass1_hypothesis_tag_to_hypo() -> None:
    assert _normalize_pass1_prose("[HYPOTHESIS] B-track draft").startswith("[HYPO]")
    assert normalize_hypo_tag_prefix("[Hypothesis] x").startswith("[HYPO]")


def test_insight_only_instruction_has_no_json_schema_demand() -> None:
    msg = build_harness_v2_insight_only_instruction(
        deterministic_payload={"full_saju": {"saju": {"year": "갑자"}}},
        lang="ko",
        sha256_hex="a" * 64,
    )
    assert "평문" in msg or "plain prose" in msg.lower()
    assert "myeongri_ai_interpretation_envelope_v1" not in msg


def test_format_wrap_instruction_pins_insight_verbatim() -> None:
    insight = "[HYPO] 테스트 해설"
    msg = build_harness_v2_format_wrap_instruction(
        deterministic_payload={"full_saju": {"saju": {"year": "갑자"}}},
        lang="ko",
        sha256_hex="b" * 64,
        pass1_insight=insight,
    )
    assert "copy verbatim" in msg.lower() or "exactly" in msg.lower()
    assert insight in msg


def test_deterministic_pass2_produces_valid_envelope_first_locked_row() -> None:
    golden_path = Path("data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl")
    row = json.loads(golden_path.read_text(encoding="utf-8").splitlines()[0])
    recomputed = build_golden_row_dict(
        str(row["birth_instant_utc"]),
        str(row["iana_tz"]),
        bool(row.get("is_male", False)),
        str(row["sample_id"]),
        "locked_eval",
    )["expected_result"]
    compact = compact_expected_result(recomputed)
    sha = sha256_canonical(compact)
    insight = _pass1_insight_dry_run(compact=compact, lang="ko", sample_id=str(row["sample_id"]))
    envelope, note, used = dual_pass_deterministic_format_v1(
        pass1_insight=insight,
        compact=compact,
        lang="ko",
        deterministic_input_sha256=sha,
    )
    assert used is True
    assert note == ""
    assert validate_envelope_required_fields(envelope) == ""
    assert envelope.get("mkm_advanced_insight", "").startswith("[HYPO]")
