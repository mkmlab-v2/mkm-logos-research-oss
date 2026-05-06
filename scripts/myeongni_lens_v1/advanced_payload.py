from __future__ import annotations

from typing import Any

from . import INPUT_SCHEMA_ADV_V1, RULESET_ID_DEFAULT
from .repro import canonical_json_sha256, digest_tag
from .school_registry import (
    KNOWN_SCHOOL_IDS,
    blend_school_direction,
    math_blend_v0_and_schools,
    normalize_weights,
    score_school_stub,
)
from .mkm_myeongni_math import compute_mkm_myeongni_math


def parse_advanced_input(raw: dict[str, Any] | None) -> dict[str, Any]:
    """고급 입력이 없으면 stub 상태의 빈 골격을 반환."""
    if not raw:
        return {
            "schema": INPUT_SCHEMA_ADV_V1,
            "status": "absent",
            "pillars": {},
            "dayun": [],
            "sajeong_interpolation": {},
            "sinsal": [],
            "schools_active": [],
            "coordinator_weights": {},
            "reference_ts_utc": None,
        }
    if str(raw.get("schema") or "") != INPUT_SCHEMA_ADV_V1:
        return {
            "schema": INPUT_SCHEMA_ADV_V1,
            "status": "invalid_schema",
            "parse_error": "expected schema myeongni_lens_advanced_input_v1",
            "pillars": {},
            "dayun": [],
            "sajeong_interpolation": {},
            "sinsal": [],
            "schools_active": [],
            "coordinator_weights": {},
            "reference_ts_utc": raw.get("reference_ts_utc"),
        }

    schools = raw.get("schools_active")
    if not isinstance(schools, list) or not schools:
        schools = ["zi_ping", "zi_wei", "mkm_coordinator_default"]
    schools_f = [str(s) for s in schools if str(s) in KNOWN_SCHOOL_IDS]
    if not schools_f:
        schools_f = ["zi_ping", "zi_wei"]

    weights_in = raw.get("coordinator_weights")
    wmap = normalize_weights(weights_in if isinstance(weights_in, dict) else None, schools_f)

    ctx = {
        "pillars": raw.get("pillars") if isinstance(raw.get("pillars"), dict) else {},
        "dayun": raw.get("dayun") if isinstance(raw.get("dayun"), list) else [],
        "sinsal": raw.get("sinsal") if isinstance(raw.get("sinsal"), list) else [],
        "sajeong_interpolation": raw.get("sajeong_interpolation")
        if isinstance(raw.get("sajeong_interpolation"), dict)
        else {},
    }

    signals = [score_school_stub(sid, ctx) for sid in schools_f]
    dir_s, conf_s = blend_school_direction(signals, wmap)

    ok_payload: dict[str, Any] = {
        "schema": INPUT_SCHEMA_ADV_V1,
        "status": "ok",
        "pillars": ctx["pillars"],
        "dayun": ctx["dayun"],
        "sajeong_interpolation": ctx["sajeong_interpolation"],
        "sinsal": ctx["sinsal"],
        "schools_active": schools_f,
        "coordinator_weights": wmap,
        "school_signals": signals,
        "school_blend": {
            "direction_score": round(dir_s, 6),
            "confidence": round(conf_s, 6),
        },
        "reference_ts_utc": raw.get("reference_ts_utc"),
    }
    if isinstance(raw.get("provenance"), dict):
        ok_payload["provenance"] = dict(raw["provenance"])
    return ok_payload


def build_v1_payload(
    base_v0: dict[str, Any],
    *,
    advanced_block: dict[str, Any],
    ruleset_id: str,
    input_digest_src: dict[str, Any],
) -> dict[str, Any]:
    """v0 페이로드 위에 v1 슬롯·재현성 메타를 얹는다."""
    d0 = float((base_v0.get("scores") or {}).get("direction_score") or 0.0)
    c0 = float((base_v0.get("scores") or {}).get("confidence") or 0.5)

    adv = advanced_block
    status = str(adv.get("status") or "")
    if status == "ok" and isinstance(adv.get("school_blend"), dict):
        d_s = float((adv["school_blend"]).get("direction_score") or 0.0)
        c_s = float((adv["school_blend"]).get("confidence") or 0.5)
        d_m, c_m = math_blend_v0_and_schools(d0, c0, d_s, c_s, alpha_v0=0.65)
        blend_note = "merged v0(0.65)+schools(0.35)"
    else:
        d_m, c_m = d0, c0
        blend_note = "advanced absent or invalid; scores equal v0"

    digest_hex = canonical_json_sha256(input_digest_src)

    out = dict(base_v0)
    out["schema"] = "myeongni_independent_lens_v1"
    out["engine_id"] = "independent_lens_v1"
    out["version"] = "1.0.0"
    out["scores"] = {
        "direction_score": round(d_m, 6),
        "confidence": round(c_m, 6),
    }
    mkm_math = compute_mkm_myeongni_math(adv)
    out["advanced"] = {
        "input_summary": adv,
        "slots": {
            "pillars": adv.get("pillars"),
            "dayun": adv.get("dayun"),
            "sajeong_interpolation": adv.get("sajeong_interpolation"),
            "sinsal": adv.get("sinsal"),
        },
        "coordinator": {
            "profile_id": "mkm_default_coordinator_v1",
            "weights_effective": adv.get("coordinator_weights") or {},
            "school_signals": adv.get("school_signals") or [],
            "blend_policy_note": blend_note,
            "mkm_myeongni_math": mkm_math,
        },
    }
    out["rules"] = {
        "ruleset_id": ruleset_id or RULESET_ID_DEFAULT,
        "hypothesis_tier": "B",
        "boundary_ack": True,
    }
    out["reproducibility"] = {
        "input_digest_sha256": digest_tag(digest_hex),
        "ruleset_id": ruleset_id or RULESET_ID_DEFAULT,
        "engine_mix": {"v0_weight": 0.65, "school_blend_weight": 0.35},
    }
    myeong_out = dict(out.get("myeongri_stream_outputs") or {})
    myeong_out["v1_blend_note"] = blend_note
    out["myeongri_stream_outputs"] = myeong_out
    out["note"] = (
        "B-track independent lens v1: extensible school/dayun/sinsal slots; "
        "numeric stub until full manseryeok bridge; not A-track / not live trigger."
    )
    return out


def build_input_digest_object(
    *,
    row_snapshot: dict[str, Any],
    advanced_path: str | None,
    advanced_doc: dict[str, Any] | None,
    momentum_window: int,
) -> dict[str, Any]:
    """재현성 해시에 들어가는 결정적 입력 묶음."""
    return {
        "experiment_tail_row": row_snapshot,
        "advanced_input_path": advanced_path or "",
        "advanced_input_doc": advanced_doc or {},
        "momentum_window": momentum_window,
    }
