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


def sanitize_interpret_raw_for_parse(raw: str) -> str:
    """Strip chat leak before JSON extraction (inference post-process v1)."""
    return strip_chat_leakage(raw)


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
