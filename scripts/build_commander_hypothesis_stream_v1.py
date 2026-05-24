#!/usr/bin/env python3
"""Rule-based morning hypothesis stream — world × myeongni [HYPO][NON_GATING].

P31a: branches + archive to reports/hypothesis_log/YYYY-MM-DD_hypothesis_log_v1.json
P31b: telegram + PersonaDiary via commander_daily_fortune telegram_append_lines.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "reports" / "hypothesis_log"
DEFAULT_LATEST = ROOT / "reports" / "commander_hypothesis_stream_latest.json"

MARKET_CAUTION = frozenset({"WATCH", "HOLD", "CAUTION", "REDUCE"})
MARKET_GO = frozenset({"GO", "TILT_UP", "BUY", "GREEN"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy_env(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _extract_myeongni_tags(myeongni_lines: List[str]) -> Dict[str, Any]:
    text = "\n".join(myeongni_lines)
    mo_tg = ""
    m = re.search(r"월운\s*\d*월?\s*\S+\((\S+)\)", text)
    if m:
        mo_tg = m.group(1)
    if "상관" in text and not mo_tg:
        mo_tg = "상관"
    school = "—"
    if "학파 혼합" in text or "hybrid" in text.lower():
        school = "hybrid_guarded"
    elif "균형" in text:
        school = "balance_centered"
    weak_fire = "화" in text and ("약" in text or "결핍" in text)
    dom = ""
    m2 = re.search(r"오행 우세\s*(\S+)\s*/\s*약\s*(\S+)", text)
    if m2:
        dom, weak = m2.group(1), m2.group(2)
        weak_fire = weak_fire or weak == "화"
        dom = dom
    ilun_reactive = "별축" in text or "외부 변수" in text
    return {
        "month_ten_god": mo_tg,
        "school_decision": school,
        "weak_fire": weak_fire,
        "dominant_element": dom,
        "ilun_reactive": ilun_reactive,
    }


def _market_tone(world: Dict[str, Any]) -> str:
    k = str(((world.get("kospi") or {}).get("today_action")) or "—").upper()
    m = str(((world.get("macro") or {}).get("decision_state")) or "—").upper()
    if k in MARKET_CAUTION or m in MARKET_CAUTION:
        return "caution"
    if k in MARKET_GO and m in MARKET_GO:
        return "go_hypo"
    return "neutral"


def _branch(
    branch_id: str,
    *,
    trigger_ko: str,
    predicted_bias_ko: str,
    confidence: str,
    collision_tags: List[str],
) -> Dict[str, Any]:
    return {
        "branch_id": branch_id,
        "trigger_ko": trigger_ko,
        "predicted_bias_ko": predicted_bias_ko,
        "confidence": confidence,
        "hypothesis_tier": "B",
        "non_gating": True,
        "collision_tags": collision_tags,
    }


def build_hypothesis_stream(
    *,
    myeongni_lines: List[str],
    world_pulse: Dict[str, Any],
    calendar_kst: str,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tags = _extract_myeongni_tags(myeongni_lines)
    tone = _market_tone(world_pulse)
    sasang = ""
    if profile:
        sasang = str(profile.get("sasang_label") or profile.get("sasang") or "").strip()
    if not sasang and isinstance(world_pulse.get("lifestyle"), dict):
        sasang = str(world_pulse["lifestyle"].get("sasang_label") or "")

    headlines = list(world_pulse.get("headlines_top_ko") or [])
    if not headlines:
        h = str(world_pulse.get("headline_ko") or "").strip()
        if h:
            headlines = [h]

    branches: List[Dict[str, Any]] = []
    mo_tg = tags.get("month_ten_god") or "—"

    if mo_tg == "상관" and tone == "caution":
        branches.append(
            _branch(
                "expr_vs_cautious_market",
                trigger_ko=f"월운 {mo_tg} + 장면/거시 {tone}",
                predicted_bias_ko="말·기획·대외 확장은 짧게 — 관측·검증 우선(과열·추격 편향 경계)",
                confidence="mid",
                collision_tags=["ten_god:상관", "market:caution"],
            )
        )
    if tags.get("weak_fire") and tone in ("caution", "neutral"):
        branches.append(
            _branch(
                "fire_deficit_noise",
                trigger_ko="약 오행 화 + 거시/뉴스 잡음",
                predicted_bias_ko="결단 속도보다 회복·수면·페이싱 — 소음(태음/소음) 보조 강화",
                confidence="mid",
                collision_tags=["element:화약", "market:noise"],
            )
        )
    if headlines and mo_tg == "상관":
        branches.append(
            _branch(
                "headline_expression_filter",
                trigger_ko=f"헤드라인 {len(headlines)}건 + 월운 {mo_tg}",
                predicted_bias_ko="뉴스 자극에 말·카피·회의가 늘기 쉬움 — 핵심 1줄만 남기고 나머지는 저녁에 재검토",
                confidence="low" if (world_pulse.get("news") or {}).get("confidence", 1) < 0.25 else "mid",
                collision_tags=["news:headline", "ten_god:상관"],
            )
        )
    if tone == "go_hypo" and tags.get("school_decision") in ("balance_centered", "hybrid_guarded"):
        branches.append(
            _branch(
                "aligned_execution_hypo",
                trigger_ko="장면·거시 관측 우위 + 명리 학파 균형",
                predicted_bias_ko="구조·체크리스트·Fact-Lock 마감에 유리 — 다만 신체 피로 시 분할 진입",
                confidence="mid",
                collision_tags=["market:go_hypo", "myeongni:balance"],
            )
        )
    if tags.get("ilun_reactive") and tone == "caution":
        branches.append(
            _branch(
                "reactive_pacing",
                trigger_ko="일운 별축 + 장면 WATCH",
                predicted_bias_ko="외부 변수에 즉답·과반응 자제 — 한 박자 늦춘 판단이 유리할 수 있음",
                confidence="mid",
                collision_tags=["ilun:reactive", "market:caution"],
            )
        )
    if sasang == "태양인" and tone == "caution":
        branches.append(
            _branch(
                "taeyang_overheat_guard",
                trigger_ko=f"체질 {sasang} + 시장 {tone}",
                predicted_bias_ko="확장·결단 에너지는 유지하되 규모는 보수 — 휴식 루틴 없으면 과열 리스크",
                confidence="mid",
                collision_tags=["sasang:태양인", "market:caution"],
            )
        )

    if len(branches) < 3:
        branches.append(
            _branch(
                "default_observe",
                trigger_ko="세상×나 기본 관측 모드",
                predicted_bias_ko="오늘은 가설 분기만 참고 — 확정·매매·임상 단정 없음",
                confidence="low",
                collision_tags=["fallback"],
            )
        )

    branches = branches[:5]
    synthesis = _synthesis_line(tags, tone, headlines, branches)

    return {
        "schema": "commander_hypothesis_stream_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "boundary_ack": True,
        "calendar_kst": calendar_kst,
        "generated_at_utc": _utc_now(),
        "myeongni_tags": tags,
        "market_tone": tone,
        "headlines_top_ko": headlines,
        "branches": branches,
        "synthesis_ko": synthesis,
        "advisory_only": True,
        "track_a_auto_order_forbidden": True,
        "upstream_schema": world_pulse.get("schema"),
    }


def _synthesis_line(
    tags: Dict[str, Any],
    tone: str,
    headlines: List[str],
    branches: List[Dict[str, Any]],
) -> str:
    mo = tags.get("month_ten_god") or "—"
    top_bias = branches[0].get("predicted_bias_ko", "") if branches else ""
    h0 = (headlines[0][:50] + "…") if headlines and len(headlines[0]) > 50 else (headlines[0] if headlines else "")
    return (
        f"초론 요약: 월운 {mo} × 판 {tone}"
        + (f" × 뉴스「{h0}」" if h0 else "")
        + f" → {top_bias[:100]}"
        + " [가설·시간창 미검증]"
    )


def append_hypothesis_telegram(
    telegram_lines: List[str],
    stream: Dict[str, Any],
) -> None:
    telegram_lines.extend(
        [
            "",
            "▸ 오늘 초론 스트림 [가설][NON_GATING]",
            f"  {stream.get('synthesis_ko', '')}",
        ]
    )
    for i, br in enumerate(stream.get("branches") or [], start=1):
        conf = br.get("confidence", "—")
        telegram_lines.append(
            f"  {i}. [{conf}] {br.get('trigger_ko', '')} → {br.get('predicted_bias_ko', '')}"
        )
    telegram_lines.append(
        "  경계: Track A·실매매 자동합선 없음 · advisory only · P31d 채점은 익일 레일"
    )


def write_hypothesis_log(
    stream: Dict[str, Any],
    *,
    fortune_path: Path,
    workspace: Path = ROOT,
) -> Path:
    cal = str(stream.get("calendar_kst") or datetime.now().strftime("%Y-%m-%d"))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out = LOG_DIR / f"{cal}_hypothesis_log_v1.json"
    envelope = {
        "schema": "commander_hypothesis_log_v1",
        "calendar_kst": cal,
        "archived_at_utc": _utc_now(),
        "fortune_path": str(fortune_path),
        "hypothesis_stream": stream,
        "evolution_rail": "P31a_archive_only",
        "next_steps": [
            "P31d: score vs KOSPI/BTC close (B-track)",
            "draft: run_autonomous_evolution_loop_draft_v1.py --dry-run",
        ],
    }
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = workspace / "reports" / "commander_hypothesis_stream_latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(stream, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def build_and_attach(
    telegram_lines: List[str],
    *,
    myeongni_lines: List[str],
    world_pulse: Dict[str, Any],
    calendar_kst: str,
    fortune_path: Path,
    profile: Optional[Dict[str, Any]] = None,
    workspace: Path = ROOT,
    archive: bool = True,
) -> Dict[str, Any]:
    stream = build_hypothesis_stream(
        myeongni_lines=myeongni_lines,
        world_pulse=world_pulse,
        calendar_kst=calendar_kst,
        profile=profile,
    )
    append_hypothesis_telegram(telegram_lines, stream)
    if archive:
        write_hypothesis_log(stream, fortune_path=fortune_path, workspace=workspace)
    return stream


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fortune-json", type=Path, default=ROOT / "reports" / "commander_daily_fortune_latest.json")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_LATEST)
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    if not args.fortune_json.is_file():
        raise SystemExit(f"missing fortune: {args.fortune_json}")

    fortune = json.loads(args.fortune_json.read_text(encoding="utf-8-sig"))
    tg = list(fortune.get("telegram_append_lines") or [])
    stream = build_and_attach(
        tg,
        myeongni_lines=fortune.get("myeongni_lines") or [],
        world_pulse=fortune.get("world_pulse_fusion") or {},
        calendar_kst=str(fortune.get("calendar_kst") or ""),
        fortune_path=args.fortune_json,
        archive=not args.no_archive,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(stream, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"branches: {len(stream.get('branches') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
