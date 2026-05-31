"""Harness v2: template interpretation envelope from deterministic engine JSON (B-track)."""

from __future__ import annotations

import hashlib
import json
import re
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


# Truncates insight *value* when the model continues in Chinese / duplicate JSON mid-string.
_INSIGHT_VALUE_LEAK_MARKERS = (
    "若要提供",
    "采用了",
    "任务：",
    "\n\n{",
    '\n{"schema":',
    '\n{\n  "schema":',
    "根据您的要求",
    "背景路径（审计）",
)


def normalize_json_punctuation_for_parse(raw: str) -> str:
    """Map common LLM curly/smart quotes to ASCII for json.loads."""
    s = raw or ""
    return (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def strip_chat_leakage(raw: str) -> str:
    """Trim common instruction-tuning leak tails before JSON parse."""
    s = normalize_json_punctuation_for_parse((raw or "").strip())
    for marker in (
        "Human:",
        "Assistant:",
        "Human：",
        "\n\nHuman",
        "\n\nUser:",
        "\nUser:",
        "\n### Instruction:",
        "\n### Response:",
        "\n\n{",
        "采用了",
        "任务：",
        "若要提供",
        "Select all correct",
        "Thank you for providing",
    ):
        if marker in s:
            s = s.split(marker, 1)[0].strip()
    m = re.search(r"\bHuman:\s*", s)
    if m:
        s = s[: m.start()].strip()
    schema = "myeongri_ai_interpretation_envelope_v1"
    first = s.find(schema)
    if first >= 0:
        second = s.find(schema, first + len(schema))
        if second > 0:
            brace = s.rfind("{", 0, second)
            if brace > 0:
                s = s[:brace].rstrip().rstrip(",").rstrip()
    return s


def extract_insight_from_raw_leak_truncated(raw: str) -> str | None:
    """Recover narrative when JSON is truncated or polluted inside mkm_advanced_insight."""
    s = normalize_json_punctuation_for_parse((raw or "").strip())
    val = ""
    m = re.search(
        r'"mkm_advanced_insight"\s*:\s*"((?:\\.|[^"\\])*)"',
        s,
        flags=re.DOTALL,
    )
    if not m:
        m = re.search(
            r'"mkm_advanced_insight"\s*:\s*"([^"\n]{8,4000})',
            s,
            flags=re.DOTALL,
        )
    if m:
        val = m.group(1)
    else:
        key = "mkm_advanced_insight"
        ki = s.find(f'"{key}"')
        if ki < 0:
            ki = s.find(key)
        if ki >= 0:
            sub = s[ki + len(key) :].lstrip()
            if sub.startswith('": "'):
                sub = sub[4:]
            elif sub.startswith('":"'):
                sub = sub[3:]
            elif sub.startswith(':"'):
                sub = sub[2:]
            elif sub.startswith(":"):
                sub = sub[1:].lstrip().lstrip('"')
            elif sub.startswith('"'):
                sub = sub[1:]
            q1 = sub.find('"')
            if q1 > 0:
                val = sub[:q1]
            elif sub:
                val = sub[:4000]
    if len(val) < 8:
        return None
    for leak in _INSIGHT_VALUE_LEAK_MARKERS:
        if leak in val:
            val = val.split(leak, 1)[0]
    val = val.strip()
    min_len = 6 if val.startswith("[HYPO]") else 8
    if len(val) < min_len:
        return None
    return val if val.startswith("[HYPO]") else f"[HYPO] {val}"


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
    raw: str | None = None,
) -> str | None:
    """Pull narrative text from flat or nested LLM envelope shapes."""
    insight = parsed.get("mkm_advanced_insight")
    if isinstance(insight, str) and len(insight.strip()) >= 8:
        val = insight.strip()
        for leak in _INSIGHT_VALUE_LEAK_MARKERS:
            if leak in val:
                val = val.split(leak, 1)[0].strip()
        if len(val) >= 8:
            return val
    if raw:
        recovered = extract_insight_from_raw_leak_truncated(raw)
        if recovered:
            return recovered
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


def augment_parsed_with_recovered_insight(
    parsed: dict[str, Any] | None,
    raw: str,
) -> dict[str, Any] | None:
    """If JSON parsed but insight empty/truncated, recover from raw text."""
    if not raw.strip():
        return parsed
    recovered = extract_insight_from_raw_leak_truncated(raw)
    if not recovered:
        return parsed
    if parsed is None:
        return {
            "schema": "myeongri_ai_interpretation_envelope_v1",
            "mkm_advanced_insight": recovered,
        }
    if not isinstance(parsed.get("mkm_advanced_insight"), str) or len(
        str(parsed.get("mkm_advanced_insight") or "").strip()
    ) < 8:
        return {**parsed, "mkm_advanced_insight": recovered}
    return parsed


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


def _ilgan_element_hint(ilgan: Any) -> str:
    """Lightweight oheng hint from day stem char (B-track narrative only)."""
    if not isinstance(ilgan, str) or not ilgan:
        return ""
    stem = ilgan[0] if ilgan else ""
    hints = {
        "甲": "목(木)",
        "乙": "목(木)",
        "丙": "화(火)",
        "丁": "화(火)",
        "戊": "토(土)",
        "己": "토(土)",
        "庚": "금(金)",
        "辛": "금(金)",
        "壬": "수(水)",
        "癸": "수(水)",
        "갑": "목(木)",
        "을": "목(木)",
        "병": "화(火)",
        "정": "화(火)",
        "무": "토(土)",
        "기": "토(土)",
        "경": "금(金)",
        "신": "금(金)",
        "임": "수(水)",
        "계": "수(水)",
    }
    return hints.get(stem, "")


def insight_variant_index(*, sample_id: str, n_variants: int = 6) -> int:
    import hashlib

    if n_variants <= 1:
        return 0
    digest = hashlib.sha256(sample_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % n_variants


def build_mkm_insight_ko_v1(
    *,
    y: Any,
    mo: Any,
    d: Any,
    h: Any,
    ilgan: Any,
    utc: str,
    tz: str,
    local_iso: str = "",
    variant: int = 0,
) -> str:
    """Deterministic [HYPO] insight variants — cite engine pillars only."""
    elem = _ilgan_element_hint(ilgan)
    elem_clause = f" 일간 {ilgan}({elem}) 중심으로" if elem else f" 일간 {ilgan} 중심으로"
    local_clause = f" 현지시각 {local_iso}." if local_iso else ""
    variants = [
        (
            f"[HYPO] 결정론 엔진 기준 사주: 년주 {y}, 월주 {mo}, 일주 {d}, 시주 {h}, 일간 {ilgan}. "
            f"가격·매매·의료 단정이 아닌 B-track 서술 초안. birth_instant_utc={utc}, iana_tz={tz}."
        ),
        (
            f"[HYPO] 엔진 산출 만세력: {y}·{mo}·{d}·{h} 네 기둥,{elem_clause} "
            f"해석 초안만 제시(확정·투자·진단 아님). UTC={utc}, TZ={tz}.{local_clause}"
        ),
        (
            f"[HYPO] B-track 명리 해설 초안 — 년 {y}, 월 {mo}, 일 {d}, 시 {h}, 일간 {ilgan}. "
            f"입력 JSON과 모순 없이 서술. birth_instant_utc={utc}, iana_tz={tz}."
        ),
        (
            f"[HYPO] Harness v2: 사주 재계산 없음. 확정된 기둥 {y}/{mo}/{d}/{h}, "
            f"일간 {ilgan}. 가격·매매·의료 단정 금지. {utc} · {tz}."
        ),
        (
            f"[HYPO] 결정론 프로필 요약: 사주({y},{mo},{d},{h}),{elem_clause} "
            f"운세·매매 단정 아님. birth_instant_utc={utc}, iana_tz={tz}.{local_clause}"
        ),
        (
            f"[HYPO] 엔진 JSON 근거 해설 — 4주 {y}·{mo}·{d}·{h}, 일간 {ilgan}. "
            f"인간 검토용 B-track 초안. UTC {utc}, IANA {tz}."
        ),
    ]
    return variants[variant % len(variants)]


def build_mkm_insight_en_v1(
    *,
    y: Any,
    mo: Any,
    d: Any,
    h: Any,
    ilgan: Any,
    utc: str,
    tz: str,
    local_iso: str = "",
    variant: int = 0,
) -> str:
    variants = [
        (
            f"[HYPO] Four pillars from deterministic engine: year={y}, month={mo}, "
            f"day={d}, hour={h}; day master={ilgan}. Narrative draft only; "
            f"not a price or trading call. birth_instant_utc={utc} iana_tz={tz}."
        ),
        (
            f"[HYPO] Engine manseryeok snapshot: {y}/{mo}/{d}/{h}, day master {ilgan}. "
            f"B-track draft only; no trading/medical claims. UTC={utc}, TZ={tz}."
        ),
    ]
    return variants[variant % len(variants)]


def template_envelope_from_compact(
    compact: dict[str, Any],
    *,
    lang: str = "ko",
    deterministic_input_sha256: str | None = None,
    method_id: str = "template_v1_from_engine_pillars",
    insight_variant: int = 0,
    sample_id: str = "",
) -> dict[str, Any]:
    """Oracle-style supervision for interpret LoRA v0 (schema compliance + pillar cite)."""
    fs = compact.get("full_saju") if isinstance(compact.get("full_saju"), dict) else {}
    saju = fs.get("saju") if isinstance(fs.get("saju"), dict) else {}
    ilgan = fs.get("ilgan")
    y, mo, d, h = saju.get("year"), saju.get("month"), saju.get("day"), saju.get("hour")
    res = compact.get("resolution") if isinstance(compact.get("resolution"), dict) else {}
    utc = res.get("birth_instant_utc", "")
    tz = res.get("iana_tz", "")
    local_iso = str(res.get("local_iso") or "")

    variant = insight_variant
    if sample_id and insight_variant == 0:
        variant = insight_variant_index(sample_id=sample_id)

    if lang == "en":
        insight = build_mkm_insight_en_v1(
            y=y, mo=mo, d=d, h=h, ilgan=ilgan, utc=str(utc), tz=str(tz),
            local_iso=local_iso, variant=variant,
        )
        prohibition = PROHIBITION_ACK_EN
    else:
        insight = build_mkm_insight_ko_v1(
            y=y, mo=mo, d=d, h=h, ilgan=ilgan, utc=str(utc), tz=str(tz),
            local_iso=local_iso, variant=variant,
        )
        prohibition = PROHIBITION_ACK_KO

    sha = deterministic_input_sha256 or sha256_canonical(compact)
    mid = method_id
    if variant:
        mid = f"{method_id}_var{variant}"
    out: dict[str, Any] = {
        "schema": "myeongri_ai_interpretation_envelope_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "mkm_advanced_insight": insight,
        "confidence_score": 0.55,
        "human_review_required": True,
        "prohibition_ack": prohibition,
        "method_id": mid,
        "deterministic_input_sha256": sha,
    }
    return out
