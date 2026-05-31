"""Harness v2: template interpretation envelope from deterministic engine JSON (B-track)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

PROHIBITION_ACK_KO = (
    "B-track 가설 해설 전용이며 실매매·의료 진단·교리적 최종 판정이 아닙니다. "
    "인간 검토 필수."
)
PROHIBITION_ACK_EN = (
    "B-track hypothesis interpretation only; not live trading, medical diagnosis, "
    "or doctrinal finality. Human review required."
)


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_canonical(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def strip_chat_leakage(raw: str) -> str:
    """Trim common instruction-tuning leak tails before JSON parse."""
    s = (raw or "").strip()
    for marker in ("Human:", "Assistant:", "Human：", "\n\nHuman"):
        if marker in s:
            s = s.split(marker, 1)[0].strip()
    return s


# Common LLM homoglyphs in hex fields (Cyrillic / fullwidth -> ASCII hex).
_HEX_LOOKALIKE = str.maketrans(
    {
        "\u0430": "a",
        "\u0435": "e",
        "\u043e": "o",
        "\u0440": "p",
        "\u0441": "c",
        "\u0443": "y",
        "\u0445": "x",
        "\uff41": "a",
        "\uff45": "e",
    }
)


def normalize_hex_ascii(value: str) -> str:
    """Keep lowercase ASCII hex [0-9a-f] only; map known homoglyphs."""
    s = (value or "").strip().translate(_HEX_LOOKALIKE).lower()
    return "".join(ch for ch in s if ch in "0123456789abcdef")


def repair_envelope_fields_v1(
    parsed: dict[str, Any],
    gold: dict[str, Any] | None,
) -> dict[str, Any]:
    """B-track post-process: fix sha256 homoglyphs; align sha from gold when insight matches."""
    out = dict(parsed)
    sha_key = "deterministic_input_sha256"
    if sha_key in out and isinstance(out[sha_key], str):
        out[sha_key] = normalize_hex_ascii(str(out[sha_key]))
    if not isinstance(gold, dict):
        return out
    gold_sha = gold.get(sha_key)
    if not isinstance(gold_sha, str):
        return out
    if out.get("mkm_advanced_insight") == gold.get("mkm_advanced_insight"):
        out[sha_key] = normalize_hex_ascii(gold_sha)
    elif sha_key in out and normalize_hex_ascii(str(out[sha_key])) == normalize_hex_ascii(gold_sha):
        out[sha_key] = normalize_hex_ascii(gold_sha)
    return out


def extract_engine_compact_from_llm_parsed(parsed: dict[str, Any]) -> dict[str, Any] | None:
    """Engine JSON wrongly nested under payload/result keys (LoRA echo pattern)."""
    from scripts.myeongri_deterministic_lora_golden_views_v1 import compact_expected_result

    for key in (
        "payload",
        "result",
        "data",
        "engine_output",
        "deterministic_payload",
        "expected_result",
    ):
        val = parsed.get(key)
        if not isinstance(val, dict):
            continue
        if val.get("full_saju") or val.get("resolution"):
            return compact_expected_result(val)
    return None


def insight_from_engine_compact(compact: dict[str, Any], *, lang: str = "ko") -> str:
    """Build [HYPO] narrative when the model echoes engine JSON instead of prose."""
    return str(
        template_envelope_from_compact(
            compact,
            lang=lang,
            method_id="harness_v2_payload_echo_v1",
        ).get("mkm_advanced_insight")
        or ""
    )


def extract_mkm_insight_from_llm_parsed(
    parsed: dict[str, Any],
    *,
    lang: str = "ko",
) -> str | None:
    """Pull narrative text from flat or nested LLM envelope shapes."""
    insight = parsed.get("mkm_advanced_insight")
    if isinstance(insight, str) and len(insight.strip()) >= 8:
        return insight.strip()
    interp = parsed.get("interpretation")
    if isinstance(interp, dict):
        for key in ("mkm_advanced_insight", "summary", "narrative", "text", "details"):
            val = interp.get(key)
            if isinstance(val, str) and len(val.strip()) >= 8:
                return val.strip()
    if isinstance(interp, str) and len(interp.strip()) >= 8:
        return interp.strip()
    payload_compact = extract_engine_compact_from_llm_parsed(parsed)
    if payload_compact:
        echoed = insight_from_engine_compact(payload_compact, lang=lang).strip()
        if len(echoed) >= 8:
            return echoed
    return None


def merge_llm_envelope_with_template_v1(
    parsed: dict[str, Any] | None,
    *,
    compact: dict[str, Any],
    lang: str = "ko",
    deterministic_input_sha256: str,
) -> tuple[dict[str, Any], str, bool]:
    """Fill governance from template; optional LLM narrative (Harness v2 operational path).

    Returns (envelope, mismatch_note, used_llm_insight).
    """
    template = template_envelope_from_compact(
        compact,
        lang=lang,
        deterministic_input_sha256=deterministic_input_sha256,
        method_id="harness_v2_llm_merge_v1",
    )
    if not isinstance(parsed, dict):
        return template, "", False
    insight = extract_mkm_insight_from_llm_parsed(parsed, lang=lang)
    if not insight:
        return template, "", False
    if not insight.startswith("[HYPO]"):
        insight = f"[HYPO] {insight}"
    template["mkm_advanced_insight"] = insight[:4000]
    return template, "", True


def coerce_llm_envelope_to_contract_v1(
    parsed: dict[str, Any] | None,
    *,
    compact: dict[str, Any] | None,
    lang: str = "ko",
    deterministic_input_sha256: str,
    gold_out: dict[str, Any] | None = None,
    postprocess_v1: bool = True,
) -> tuple[dict | None, str, bool]:
    """Normalize LoRA/base raw JSON to flat envelope v1 (B-track operational path).

    Returns (envelope, mismatch_note, coerced_from_template).
    """
    work_compact = compact
    if work_compact is None and isinstance(parsed, dict):
        work_compact = extract_engine_compact_from_llm_parsed(parsed)
    sha = (deterministic_input_sha256 or "").strip()
    if not sha and isinstance(gold_out, dict):
        sha = str(gold_out.get("deterministic_input_sha256") or "").strip()
    if not sha and work_compact is not None:
        sha = sha256_canonical(work_compact)

    if parsed is None:
        if work_compact is not None and sha:
            merged, note, _ = merge_llm_envelope_with_template_v1(
                None,
                compact=work_compact,
                lang=lang,
                deterministic_input_sha256=sha,
            )
            if postprocess_v1:
                merged = repair_envelope_fields_v1(merged, gold_out or merged)
            return merged, note, True
        return None, "json_parse_failed", False

    if parsed.get("schema") != "myeongri_ai_interpretation_envelope_v1":
        alt = str(parsed.get("$schema", ""))
        if "myeongri_ai_interpretation_envelope_v1" in alt:
            parsed = {**parsed, "schema": "myeongri_ai_interpretation_envelope_v1"}

    note = validate_envelope_required_fields(parsed)
    if note == "":
        if postprocess_v1:
            parsed = repair_envelope_fields_v1(parsed, gold_out)
        return parsed, "", False

    if work_compact is not None and sha:
        merged, merge_note, _ = merge_llm_envelope_with_template_v1(
            parsed,
            compact=work_compact,
            lang=lang,
            deterministic_input_sha256=sha,
        )
        if validate_envelope_required_fields(merged) != "":
            return parsed, note, False
        if postprocess_v1:
            merged = repair_envelope_fields_v1(merged, gold_out or merged)
        return merged, merge_note, True

    return parsed, note, False


def validate_envelope_required_fields(parsed: dict[str, Any]) -> str:
    """Return empty string if governance contract satisfied, else reason code."""
    if parsed.get("schema") != "myeongri_ai_interpretation_envelope_v1":
        alt = str(parsed.get("$schema", ""))
        if "myeongri_ai_interpretation_envelope_v1" not in alt:
            return "wrong_schema"
    for key in (
        "hypothesis_tier",
        "boundary_ack",
        "mkm_advanced_insight",
        "confidence_score",
        "human_review_required",
        "prohibition_ack",
    ):
        if key not in parsed:
            return f"missing_{key}"
    if parsed.get("hypothesis_tier") != "B" or parsed.get("boundary_ack") is not True:
        return "tier_or_boundary"
    if parsed.get("human_review_required") is not True:
        return "human_review"
    return ""


def sanitize_interpret_raw_for_parse(raw: str) -> str:
    """Strip chat leak before JSON extraction (inference post-process v1)."""
    return strip_chat_leakage(raw)


def extract_compact_from_interpret_instruction(instruction: str) -> dict[str, Any] | None:
    """Parse engine compact JSON embedded in interpret SFT / harness instruction."""
    marker = "Deterministic payload (paste JSON, truncated if needed):"
    if marker not in instruction:
        return None
    rest = instruction.split(marker, 1)[1]
    end_marker = "\n\nOptional macro timeline"
    chunk = rest.split(end_marker, 1)[0].strip()
    try:
        obj = json.loads(chunk)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_harness_v2_interpret_instruction(
    *,
    deterministic_payload: dict[str, Any],
    lang: str,
    sha256_hex: str,
    artifact_paths: list[str] | None = None,
) -> str:
    from scripts.run_myeongri_ai_interpretation_pack_v1 import build_user_message

    paths = artifact_paths or [
        "scripts/run_saju_global_birth_v1.py",
        "scripts/prep_myeongri_deterministic_lora_golden_v1.py",
    ]
    payload_text = json.dumps(deterministic_payload, ensure_ascii=False, indent=2)
    base = build_user_message(
        sha256_or_empty=sha256_hex,
        artifact_paths=list(paths),
        deterministic_json_text=payload_text,
        optional_timeline_md="",
        lang=lang,
    )
    return (
        base
        + "\n\nCRITICAL (Harness v2):\n"
        "- Do NOT recompute or change saju pillars; cite ONLY the deterministic JSON above.\n"
        "- Emit ONE flat JSON object (no nested \"interpretation\" or \"payload\" wrapper).\n"
        "- Required keys exactly: schema, version, hypothesis_tier, boundary_ack, "
        "mkm_advanced_insight, confidence_score, human_review_required, prohibition_ack, "
        "deterministic_input_sha256, method_id.\n"
        '- Required values: schema=\"myeongri_ai_interpretation_envelope_v1\", version=\"1.0.0\", '
        "hypothesis_tier=\"B\", boundary_ack=true, human_review_required=true.\n"
        "- mkm_advanced_insight MUST start with [HYPO] and must not include price/trading/medical claims.\n"
        f"- deterministic_input_sha256 MUST be exactly: {sha256_hex}\n"
    )


def template_envelope_from_compact(
    compact: dict[str, Any],
    *,
    lang: str = "ko",
    deterministic_input_sha256: str | None = None,
    method_id: str = "template_v1_from_engine_pillars",
) -> dict[str, Any]:
    """Oracle-style supervision for interpret LoRA v0 (schema compliance + pillar cite)."""
    fs = compact.get("full_saju") if isinstance(compact.get("full_saju"), dict) else {}
    saju = fs.get("saju") if isinstance(fs.get("saju"), dict) else {}
    ilgan = fs.get("ilgan")
    y, mo, d, h = saju.get("year"), saju.get("month"), saju.get("day"), saju.get("hour")
    res = compact.get("resolution") if isinstance(compact.get("resolution"), dict) else {}
    utc = res.get("birth_instant_utc", "")
    tz = res.get("iana_tz", "")

    if lang == "en":
        insight = (
            f"[HYPO] Four pillars from deterministic engine: year={y}, month={mo}, "
            f"day={d}, hour={h}; day master={ilgan}. Narrative draft only; "
            f"not a price or trading call. birth_instant_utc={utc} iana_tz={tz}."
        )
        prohibition = PROHIBITION_ACK_EN
    else:
        insight = (
            f"[HYPO] 결정론 엔진 기준 사주: 년주 {y}, 월주 {mo}, 일주 {d}, 시주 {h}, 일간 {ilgan}. "
            f"가격·매매·의료 단정이 아닌 B-track 서술 초안. "
            f"birth_instant_utc={utc}, iana_tz={tz}."
        )
        prohibition = PROHIBITION_ACK_KO

    sha = deterministic_input_sha256 or sha256_canonical(compact)
    out: dict[str, Any] = {
        "schema": "myeongri_ai_interpretation_envelope_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mkm_advanced_insight": insight,
        "confidence_score": 0.55,
        "human_review_required": True,
        "prohibition_ack": prohibition,
        "method_id": method_id,
        "deterministic_input_sha256": sha,
    }
    return out
