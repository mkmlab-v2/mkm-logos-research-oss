#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build IWS v2 seed JSON from patient_consult_input_v1 (+ optional overrides)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SASANG_MAP = {
    "taeyang": "taeyang",
    "soyang": "soyang",
    "soyag": "soyang",
    "taeum": "taeum",
    "taeeum": "taeum",
    "soeum": "soeum",
    "unknown": "unknown",
}

TOPIC_BY_COMPLAINT = {
    "복부": "abdominal_adiposity_core",
    "뱃": "abdominal_adiposity_core",
    "비만": "abdominal_adiposity_core",
    "체중": "abdominal_adiposity_core",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_band_from_utc(birth_instant_utc: str, ref: datetime | None = None) -> str:
    ref = ref or datetime.now(timezone.utc)
    birth = datetime.fromisoformat(birth_instant_utc.replace("Z", "+00:00"))
    years = (ref - birth).days / 365.25
    if years < 18:
        return "minor"
    if years < 35:
        return "young_adult"
    if years < 55:
        return "midlife"
    if years >= 55:
        return "senior"
    return "unknown"


def _topic_id(chief_complaint: str) -> str:
    text = chief_complaint or ""
    for key, topic in TOPIC_BY_COMPLAINT.items():
        if key in text:
            return topic
    return "general_wellness_core"


def _myeongni_stub_from_birth(
    birth_instant_utc: str,
    iana_tz: str,
    *,
    is_male: bool = True,
    growth_phase: bool = False,
) -> tuple[str, str]:
    """Deterministic 만세력 四柱 → IWS 명리 HYPO stub (not full lens chain)."""
    try:
        from scripts.manseryeok_perfect_final import PerfectManseryeok
        from scripts.saju_birth_resolver_v1 import resolve_from_utc_instant
    except ImportError:
        band = "성장기·회복 우선" if growth_phase else "성인 리듬"
        return (
            "명리 시간축 참고 (스텁)",
            f"만세력 엔진 모듈 미로드 — {band} 밴드 스텁으로 오버레이합니다.",
        )

    try:
        res = resolve_from_utc_instant(birth_instant_utc, iana_tz)
        full = PerfectManseryeok().calculate_full_saju_perfect(
            res.engine_year,
            res.engine_month,
            res.engine_day,
            res.engine_hour,
            is_solar=True,
            is_male=is_male,
        )
        saju = full.get("saju") or {}
        pillars = f"{saju.get('year', '?')} {saju.get('month', '?')} {saju.get('day', '?')} {saju.get('hour', '?')}"
        ilgan = full.get("ilgan", "?")
        growth_note = "성장기·회복 우선 밴드" if growth_phase else "성인 리듬 밴드"
        quant_line = ""
        try:
            from scripts.myeongni_lens_v1.mkm_myeongni_math import compute_quant_profile_v0

            quant = compute_quant_profile_v0({"pillars": saju})
            mass = quant.get("five_element_mass_vector_v0") or {}
            quant_line = (
                f" 오행 분포(정량·[HYPO]): 목={mass.get('목', 0)}·화={mass.get('화', 0)}·토={mass.get('토', 0)}"
                f"·금={mass.get('금', 0)}·수={mass.get('수', 0)} · 불균형지수={quant.get('five_element_imbalance_entropy_0_1', 0)}."
            )
        except Exception:
            quant_line = ""

        body = (
            f"출생 instant `{birth_instant_utc}` · `{iana_tz}` 기준 사주(년·월·일·시): **{pillars}** · 일간 **{ilgan}**. "
            f"[HYPO] 중단기 생활 리듬 참고용이며 임상·투자 트리거가 아닙니다. 현재 오버레이: {growth_note}.{quant_line}"
        )
        return ("명리 시간축 (만세력 四柱)", body)
    except Exception as exc:
        band = "성장기·회복 우선" if growth_phase else "성인 리듬"
        return (
            "명리 시간축 참고 (스텁)",
            f"만세력 연동 실패({exc}) — {band} 밴드 스텁으로 오버레이합니다.",
        )


def _patch_myeongni_node(seed: dict[str, Any], title: str, body: str) -> None:
    for node in seed.get("evidence_nodes_seed") or []:
        if node.get("node_id") == "myeongni_temporal_stub":
            node["source_ref"] = "manseryeok_perfect_final_v1"
            node["content_payload"] = {"title": title, "body": body}
            return


def build_seed(
    consult: dict[str, Any],
    *,
    sasang_override: str | None = None,
    growth_phase_override: bool | None = None,
    isa_angle: str = "unknown",
    zoa_status: str = "unknown",
    template_path: Path | None = None,
) -> dict[str, Any]:
    lane_a = consult.get("lane_a_profile") or {}
    lane_b = consult.get("lane_b_clinical") or {}
    birth = (lane_a.get("birth_instant_utc") or "").strip()
    tz = (lane_a.get("iana_tz") or "Asia/Seoul").strip()
    if not birth:
        raise ValueError("birth_instant_utc required")

    age_band = _age_band_from_utc(birth)
    growth = growth_phase_override if growth_phase_override is not None else age_band == "minor"

    sasang_raw = (sasang_override or consult.get("sasang_internal") or "unknown").lower()
    sasang = SASANG_MAP.get(sasang_raw, "unknown")

    chief = (lane_b.get("chief_complaint") or "웰니스 상담").strip()
    topic_id = _topic_id(chief)

    if template_path and template_path.is_file():
        seed = json.loads(template_path.read_text(encoding="utf-8-sig"))
    else:
        default_tpl = (
            ROOT
            / "docs"
            / "final"
            / "artifacts"
            / "fixtures"
            / "integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json"
        )
        seed = json.loads(default_tpl.read_text(encoding="utf-8-sig"))

    seed["metadata"]["generated_at_utc"] = _now_utc()
    seed["metadata"]["solution_id"] = f"iws_v2_{consult.get('request_id', 'anon')}"

    seed["client_profile"].update(
        {
            "birth_instant_utc": birth,
            "iana_tz": tz,
            "computed_age_band": age_band,
            "gender": consult.get("gender") or "unspecified",
            "growth_phase": growth,
            "biometrics": {"isa_angle": isa_angle, "zoa_status": zoa_status},
            "sasang_internal": sasang,
        }
    )
    seed["chief_concern"] = {
        "topic_id": topic_id,
        "title_ko": chief if chief else seed["chief_concern"]["title_ko"],
    }

    gender = (consult.get("gender") or "unspecified").lower()
    is_male = gender != "female"
    myeongni_title, myeongni_body = _myeongni_stub_from_birth(
        birth,
        tz,
        is_male=is_male,
        growth_phase=growth,
    )
    _patch_myeongni_node(seed, myeongni_title, myeongni_body)

    return seed


def main() -> int:
    parser = argparse.ArgumentParser(description="Build IWS v2 seed from consult JSON")
    parser.add_argument("--consult-json", required=True, type=Path)
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--template-json", type=Path)
    parser.add_argument("--sasang", type=str)
    parser.add_argument("--growth-phase", action="store_true")
    parser.add_argument("--no-growth-phase", action="store_true")
    args = parser.parse_args()

    consult = json.loads(args.consult_json.read_text(encoding="utf-8-sig"))
    growth = None
    if args.growth_phase:
        growth = True
    elif args.no_growth_phase:
        growth = False

    seed = build_seed(
        consult,
        sasang_override=args.sasang,
        growth_phase_override=growth,
        template_path=args.template_json,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
