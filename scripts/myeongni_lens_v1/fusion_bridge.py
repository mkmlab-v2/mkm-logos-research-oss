"""MyeongriCompleteFusion·commander report 산출 → myeongni_lens_advanced_input_v1 조립."""

from __future__ import annotations

from typing import Any

from . import INPUT_SCHEMA_ADV_V1


def unwrap_fusion_payload(doc: Any) -> dict[str, Any] | None:
    """
    지원 래퍼:
    - MyeongriCompleteFusion.calculate_complete_fusion() 결과 (최상위에 ``saju``)
    - ``build_myeongni_track_b_commander_report_v1`` 산출의 ``full_fusion_payload``
    """
    if not isinstance(doc, dict):
        return None
    if isinstance(doc.get("saju"), dict) and len(doc["saju"]) >= 1:
        return doc
    ffp = doc.get("full_fusion_payload")
    if isinstance(ffp, dict) and isinstance(ffp.get("saju"), dict):
        return ffp
    return None


def build_advanced_input_from_fusion(
    fus: dict[str, Any],
    *,
    schools_active: list[str] | None = None,
    coordinator_weights: dict[str, float] | None = None,
    reference_ts_utc: str | None = None,
) -> dict[str, Any]:
    """융합 dict → 렌즈 고급 입력 v1 (신살 미계산 시 빈 배열)."""
    saju = fus.get("saju") or {}
    pillars = {
        "year": str(saju.get("year") or ""),
        "month": str(saju.get("month") or ""),
        "day": str(saju.get("day") or ""),
        "hour": str(saju.get("hour") or ""),
    }

    dayun: list[dict[str, Any]] = []
    for row in fus.get("daewoon_v1") or []:
        if not isinstance(row, dict):
            continue
        pillar = str(row.get("saju") or "")
        entry: dict[str, Any] = {
            "pillar": pillar,
            "start_age": row.get("age_start"),
            "end_age": row.get("age_end"),
        }
        for opt in ("cycle", "direction", "schema", "qiyun_applied"):
            if opt in row:
                entry[opt] = row[opt]
        dayun.append(entry)

    jig = fus.get("jijangan_v1") or {}
    pillars_overlay = jig.get("pillars") or {}
    sajeong_interpolation: dict[str, Any] = {}
    for pk in ("year", "month", "day", "hour"):
        p = pillars_overlay.get(pk) if isinstance(pillars_overlay.get(pk), dict) else {}
        ji = str(p.get("ji") or "")
        hs = p.get("hidden_stems") or []
        gans: list[str] = []
        if isinstance(hs, list):
            for h in hs:
                if isinstance(h, dict) and h.get("gan"):
                    gans.append(str(h["gan"]))
        sajeong_interpolation[pk] = {"ji": ji or None, "hidden_gans": gans}

    qiy = fus.get("daewoon_qiyun_v1") if isinstance(fus.get("daewoon_qiyun_v1"), dict) else {}

    provenance: dict[str, Any] = {
        "bridge": "myeongni_lens_v1.fusion_bridge",
        "jijangan_lut_version": jig.get("lut_version"),
        "rule_school_policy_version": (fus.get("rule_school_mkm_4d_v1") or {}).get("version"),
        "sinsal_status": "not_computed_in_bridge_v1",
    }
    if qiy:
        provenance["qiyun_schema"] = qiy.get("schema")
        if "qiyun_years_float" in qiy:
            provenance["qiyun_years_float"] = qiy.get("qiyun_years_float")

    out: dict[str, Any] = {
        "schema": INPUT_SCHEMA_ADV_V1,
        "schools_active": list(schools_active)
        if schools_active
        else ["zi_ping", "zi_wei", "mkm_coordinator_default"],
        "coordinator_weights": dict(coordinator_weights) if coordinator_weights else {},
        "pillars": pillars,
        "dayun": dayun,
        "sajeong_interpolation": sajeong_interpolation,
        "sinsal": [],
        "reference_ts_utc": reference_ts_utc,
        "provenance": provenance,
    }
    return out
