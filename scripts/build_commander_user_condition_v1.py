#!/usr/bin/env python3
"""Commander user_condition_v1 + advisory investment-bias tilt [HYPO][research_only].

P31c — derived from profile, lifestyle, world_pulse; no Track A orders.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
DEFAULT_OUT = ROOT / "reports" / "commander_user_condition_latest.json"

VALID_BANDS = frozenset({"low", "mid", "good", "high"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_band(name: str) -> Optional[str]:
    raw = (os.environ.get(name) or "").strip().lower()
    if raw in VALID_BANDS:
        return raw
    return None


def _infer_energy_band(
    lifestyle: Dict[str, Any],
    report: Dict[str, Any],
) -> str:
    override = _env_band("MKM_COMMANDER_ENERGY_BAND")
    if override:
        return override
    weak = str(lifestyle.get("weakest_element") or "")
    band = str(lifestyle.get("weather_band") or "mild")
    if weak == "화":
        return "low"
    if band in ("rain", "snow", "cold"):
        return "mid"
    if band == "hot":
        return "mid"
    return "good"


def _infer_stress_band(world_pulse: Dict[str, Any]) -> str:
    override = _env_band("MKM_COMMANDER_STRESS_BAND")
    if override:
        return override
    macro = world_pulse.get("macro") or {}
    risk = str(macro.get("risk_warning_level") or "").lower()
    k_action = str((world_pulse.get("kospi") or {}).get("today_action") or "").upper()
    if risk in ("elevated", "high", "critical") or k_action in ("WATCH", "HOLD", "REDUCE"):
        return "high"
    if risk in ("moderate", "mid"):
        return "mid"
    return "low"


def _infer_sleep_band() -> str:
    return _env_band("MKM_COMMANDER_SLEEP_BAND") or "mid"


def build_advisory_investment_bias_tilt(
    *,
    user_condition: Dict[str, Any],
    world_pulse: Dict[str, Any],
    hypothesis_stream: Dict[str, Any],
) -> Dict[str, Any]:
    """Research-only posture hint — not a trade signal."""
    tone = str(hypothesis_stream.get("market_tone") or "neutral")
    stress = user_condition.get("stress_band", "mid")
    energy = user_condition.get("energy_band", "mid")
    mo_tg = (hypothesis_stream.get("myeongni_tags") or {}).get("month_ten_god") or "—"

    if tone == "caution" and stress in ("high", "mid"):
        tilt = "observe_defensive"
        tilt_ko = "관측·방어적 페이싱 — 신규 확장·레버리지 가정은 보류 [가설]"
    elif tone == "go_hypo" and energy == "good" and stress == "low":
        tilt = "structured_participation_hypo"
        tilt_ko = "구조화된 참여 가설만 — Fact-Lock·체크리스트 후 소규모 시도 [가설]"
    elif mo_tg == "상관" and tone == "caution":
        tilt = "expression_vs_market_friction"
        tilt_ko = "말·기획 에너지와 시장 경계 충돌 — 대외 커뮤니케이션 과잉 자제 [가설]"
    else:
        tilt = "neutral_observe"
        tilt_ko = "중립 관측 — 투자·실매매 단정 없음 · 개인 에너지 우선 [가설]"

    return {
        "schema": "commander_advisory_investment_bias_tilt_v1",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_a_auto_order_forbidden": True,
        "advisory_only": True,
        "tilt_label": tilt,
        "tilt_ko": tilt_ko,
        "rationale_ko": (
            f"입력: market_tone={tone}, stress={stress}, energy={energy}, 월운={mo_tg} "
            "— 개인 명리·세상 판 겹침 해석만, 주문 트리거 아님."
        ),
        "forbidden": ["live_order", "track_a_promotion", "clinical_claim"],
    }


def build_user_condition(
    *,
    profile: Dict[str, Any],
    report: Dict[str, Any],
    lifestyle: Dict[str, Any],
    world_pulse: Dict[str, Any],
    hypothesis_stream: Dict[str, Any],
    calendar_kst: Optional[str] = None,
) -> Dict[str, Any]:
    now_kst = datetime.now(KST)
    cal = calendar_kst or now_kst.strftime("%Y-%m-%d")
    sasang = str(
        lifestyle.get("sasang_label")
        or ((profile.get("sasang_reference") or {}).get("label"))
        or "—"
    )
    digestion_note = ""
    avoid = (lifestyle.get("meals") or {}).get("avoid_ko") or []
    if avoid:
        digestion_note = f"식이: {', '.join(avoid[:2])}"

    condition = {
        "schema": "commander_user_condition_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "calendar_kst": cal,
        "generated_at_utc": _utc_now(),
        "sleep_band": _infer_sleep_band(),
        "energy_band": _infer_energy_band(lifestyle, report),
        "stress_band": _infer_stress_band(world_pulse),
        "digestion_note_ko": digestion_note,
        "sasang_label": sasang,
        "weather_band": lifestyle.get("weather_band"),
        "bio_synthesis_ko": _bio_synthesis(lifestyle, report, profile),
        "self_report_source": "derived_plus_env_optional",
    }
    condition["advisory_investment_bias_tilt"] = build_advisory_investment_bias_tilt(
        user_condition=condition,
        world_pulse=world_pulse,
        hypothesis_stream=hypothesis_stream,
    )
    return condition


def _bio_synthesis(
    lifestyle: Dict[str, Any],
    report: Dict[str, Any],
    profile: Dict[str, Any],
) -> str:
    weak = lifestyle.get("weakest_element") or "—"
    dom = lifestyle.get("dominant_element") or "—"
    sasang = lifestyle.get("sasang_label") or "—"
    patterns = (profile.get("cognition_hypothesis") or {}).get("patterns") or []
    p0 = str(patterns[0])[:80] if patterns else ""
    return (
        f"체질 {sasang} · 오행 우세 {dom}/약 {weak} · "
        f"{p0 or '에너지 페이싱 우선'} [가설·임상 단정 없음]"
    )


def append_user_condition_telegram(
    telegram_lines: List[str],
    condition: Dict[str, Any],
) -> None:
    tilt = condition.get("advisory_investment_bias_tilt") or {}
    telegram_lines.extend(
        [
            "",
            "▸ 오늘 컨디션·바이어스 틸트 [가설][research_only]",
            f"  수면·에너지·스트레스: {condition.get('sleep_band')}/{condition.get('energy_band')}/{condition.get('stress_band')}",
            f"  바이오 합성: {condition.get('bio_synthesis_ko', '')}",
            f"  투자 바이어스(참고): {tilt.get('tilt_ko', '—')}",
            "  경계: 실매매·Track A 자동합선 없음 · 주문 아님",
        ]
    )


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fortune-json", type=Path, default=ROOT / "reports" / "commander_daily_fortune_latest.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    fortune = json.loads(args.fortune_json.read_text(encoding="utf-8-sig"))
    profile = json.loads(Path(fortune["profile_path"]).read_text(encoding="utf-8-sig"))
    report = json.loads(Path(fortune["report_path"]).read_text(encoding="utf-8-sig"))
    doc = build_user_condition(
        profile=profile,
        report=report,
        lifestyle=fortune.get("lifestyle_concierge") or {},
        world_pulse=fortune.get("world_pulse_fusion") or {},
        hypothesis_stream=fortune.get("hypothesis_stream") or {},
        calendar_kst=fortune.get("calendar_kst"),
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
