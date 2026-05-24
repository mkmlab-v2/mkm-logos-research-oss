#!/usr/bin/env python3
"""O-P31c — YouTube channel / live / Shorts copy packs (KO+EN, Fact-Lock tone)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "radio_youtube_channel_copy_v1_latest.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "artifacts" / "schemas" / "radio_youtube_channel_copy_v1.schema.json"

PUBLIC_FACING_VERSION = "1.7"

# Published MKM Field Radio (Studio 2026-05-22) — preserved across rebuilds.
MKM_YOUTUBE_PUBLISHED: Dict[str, str] = {
    "youtube_channel_id": "UCksPLqCn9KrFmNVFOByEx3w",
    "youtube_channel_url": "https://www.youtube.com/channel/UCksPLqCn9KrFmNVFOByEx3w",
    "youtube_handle_url": "https://www.youtube.com/@MKMFieldRadio",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pack(
    *,
    skin_id: str,
    role: str,
    display_name_primary: str,
    display_name_secondary: str,
    handle_suggestion: str,
    description_ko: str,
    description_en: str,
    tags_ko: List[str],
    tags_en: List[str],
    live_stream_title_ko: str,
    live_stream_title_en: str,
    shorts_hashtags: List[str],
    copy_guard_notes: List[str],
) -> Dict[str, Any]:
    return {
        "skin_id": skin_id,
        "role": role,
        "display_name_primary": display_name_primary,
        "display_name_secondary": display_name_secondary,
        "handle_suggestion": handle_suggestion,
        "description_ko": description_ko,
        "description_en": description_en,
        "tags_ko": tags_ko,
        "tags_en": tags_en,
        "live_stream_title_ko": live_stream_title_ko,
        "live_stream_title_en": live_stream_title_en,
        "shorts_hashtags": shorts_hashtags,
        "copy_guard_notes": copy_guard_notes,
    }


def build_copy() -> Dict[str, Any]:
    from scripts.mkm_radio_dialogue_guard_v1 import DISCLAIMER_TEXT_KO as MKM_DISC
    from scripts.tkm_health_dialogue_guard_v1 import DISCLAIMER_TEXT_KO as TKM_DISC

    mkm_notes = [
        "No prices, hit-rate %, or buy/sell language in channel name or description.",
        "Logos / Bible lens: observational only — not investment advice.",
        "Engineering framing: Field + 3-lens (Sasang / Myeongni / Logos) — not hidden.",
    ]
    tkm_notes = [
        "No diagnosis, prescription, cure, or constitution-deterministic claims.",
        "Wellness / rhythm framing only — not a clinic or telemedicine channel.",
        "Korean-primary audience; English subtitle for discoverability.",
    ]
    zone_notes = [
        "24h ambient Zone A — burn-in disclaimer matches manifest caption_config.",
        "Prefer dedicated live stream title; channel may be shared with MKM Field Radio.",
    ]

    doc: Dict[str, Any] = {
        "schema": "radio_youtube_channel_copy_v1",
        "generated_at_utc": _utc_now(),
        "public_facing_version": PUBLIC_FACING_VERSION,
        "channels": {
            "mkm_radio": _pack(
                skin_id="mkm_radio",
                role="zone_b_mkm_shorts_vod",
                display_name_primary="MKM Field Radio",
                display_name_secondary="시장·레짐 브리핑 (비투자 자문)",
                handle_suggestion="@MKMFieldRadio",
                description_ko=(
                    "MKM Field Radio는 시장·거시·레짐을 **관측·페이싱** 관점으로 짧게 풀어 주는 채널입니다. "
                    "사상·명리·성경(Logos) 3렌즈는 보조 해설이며, 매수·매도·목표가·적중률 수치는 방송하지 않습니다.\n\n"
                    f"면책: {MKM_DISC}\n\n"
                    "더 읽기: jema-ai.com · mkmlife.com (원퀘스천)"
                ),
                description_en=(
                    "MKM Field Radio offers **observational** briefings on market context, regime, and pacing — "
                    "not investment advice. Three lenses (Sasang / Myeongni / Logos) are supplementary; "
                    "no prices, targets, or performance % on air.\n\n"
                    f"Disclaimer (KO): {MKM_DISC}\n\n"
                    "Learn more: jema-ai.com · mkmlife.com"
                ),
                tags_ko=[
                    "시장브리핑",
                    "레짐",
                    "관측",
                    "페이싱",
                    "MKM",
                    "비투자자문",
                    "다중렌즈",
                ],
                tags_en=[
                    "market context",
                    "regime watch",
                    "observational",
                    "pacing",
                    "MKM",
                    "not financial advice",
                    "multi-lens",
                ],
                live_stream_title_ko="[LIVE] MKM Field — 관측·레짐 ambient (참고용)",
                live_stream_title_en="[LIVE] MKM Field — observational regime ambient",
                shorts_hashtags=[
                    "#MKMFieldRadio",
                    "#RegimeWatch",
                    "#ObservationalOnly",
                    "#NotFinancialAdvice",
                ],
                copy_guard_notes=mkm_notes,
            ),
            "tkm_health_24h": _pack(
                skin_id="tkm_health_24h",
                role="zone_b_tkm_health_shorts",
                display_name_primary="TKM Rhythm & Rest",
                display_name_secondary="한의 웰니스 라이브 (비진료)",
                handle_suggestion="@TKMRhythmRest",
                description_ko=(
                    "TKM Rhythm & Rest는 전통 리듬·생활 습관·회복 페이싱을 **참고용**으로 다룹니다. "
                    "진료·처방·완치·체질 확정을 말하지 않으며, 증상이 있으면 의료기관을 방문하세요.\n\n"
                    f"면책: {TKM_DISC}\n\n"
                    "웰니스 이어하기: mkmlife.com"
                ),
                description_en=(
                    "TKM Rhythm & Rest shares **wellness-oriented** rhythm, habit, and recovery pacing — "
                    "not medical care. No diagnosis, prescriptions, cures, or constitution claims.\n\n"
                    f"Disclaimer (KO): {TKM_DISC}\n\n"
                    "Continue at mkmlife.com"
                ),
                tags_ko=[
                    "한의웰니스",
                    "생활리듬",
                    "회복",
                    "비진료",
                    "참고용",
                    "TKM",
                    "페이싱",
                ],
                tags_en=[
                    "wellness",
                    "daily rhythm",
                    "recovery pacing",
                    "not medical advice",
                    "TKM",
                    "holistic habits",
                    "non-clinical",
                ],
                live_stream_title_ko="[LIVE] TKM — 리듬·휴식 24h (참고용·비진료)",
                live_stream_title_en="[LIVE] TKM — rhythm & rest 24h (wellness only)",
                shorts_hashtags=[
                    "#TKMRhythmRest",
                    "#WellnessOnly",
                    "#NotMedicalAdvice",
                    "#DailyRhythm",
                ],
                copy_guard_notes=tkm_notes,
            ),
            "zone_a_ambient_24h": _pack(
                skin_id="mkm_radio",
                role="zone_a_youtube_live_rtmp",
                display_name_primary="MKM Field Radio",
                display_name_secondary="24h Oracle Sphere · ambient",
                handle_suggestion="@MKMFieldRadio",
                description_ko=(
                    "24시간 ambient 라이브: 자작 BGM + 정적 비주얼 + 주기적 면책 자막. "
                    "투자·의료·법률 자문이 아니며, 실시간 DJ 대화 없음.\n\n"
                    f"면책: {MKM_DISC}"
                ),
                description_en=(
                    "24h ambient live: self-generated BGM, idle visual, periodic disclaimer burn-in. "
                    "No investment, medical, or legal advice; no live DJ chat.\n\n"
                    f"Disclaimer (KO): {MKM_DISC}"
                ),
                tags_ko=["24시간라이브", "ambient", "MKM", "관측", "비투자자문", "oracle"],
                tags_en=[
                    "24h live",
                    "ambient",
                    "MKM",
                    "observational",
                    "not financial advice",
                    "lofi",
                ],
                live_stream_title_ko="MKM Oracle Sphere — 24h ambient [관측·참고용]",
                live_stream_title_en="MKM Oracle Sphere — 24h ambient [observational]",
                shorts_hashtags=["#MKMFieldRadio", "#AmbientLive", "#ObservationalOnly"],
                copy_guard_notes=zone_notes,
            ),
        },
        "studio_paste_order": [
            "1. YouTube Studio → 사용자 설정 → 채널 → 이름: display_name_primary + secondary",
            "2. 설명: description_ko (국내) 또는 description_en (글로벌) — 둘 다 넣지 말고 하나 선택",
            "3. 라이브 제목: live_stream_title_* at stream start",
            "4. Shorts: shorts_hashtags + tags_* (YouTube tag limit ~500 chars)",
        ],
    }
    for key in ("mkm_radio", "zone_a_ambient_24h"):
        doc["channels"][key].update(MKM_YOUTUBE_PUBLISHED)
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Build radio YouTube channel copy JSON.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = build_copy()
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(payload)
        return 0
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(payload + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
