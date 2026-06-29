#!/usr/bin/env python3
"""O-P31c — frozen guard copy (KO/EN) + Studio paste blocks (PUBLIC_FACING v1.7)."""

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

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "radio_op31c_guard_copy_v1_latest.json"
PUBLIC_FACING_VERSION = "1.7"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _b(ko: str, en: str) -> Dict[str, str]:
    return {"ko": ko.strip(), "en": en.strip()}


def build_guard_copy() -> Dict[str, Any]:
    from scripts.mkm_radio_dialogue_guard_v1 import DISCLAIMER_TEXT_KO as MKM_DISC
    from scripts.tkm_health_dialogue_guard_v1 import DISCLAIMER_TEXT_KO as TKM_DISC

    mkm_core_ko = MKM_DISC
    mkm_core_en = (
        "Not investment, medical, or legal advice. Multi-lens commentary is observational "
        "pacing only; you are responsible for your own decisions."
    )

    delayed_ko = (
        "본 화면·음성은 리스크·레짐 **관측 상태**를 전달하는 **지연·추상** 참고 자료입니다. "
        "실시간 무지연 매매·검증된 수익·적중률을 보장하지 않습니다. "
        "공개 관측 보드: jemaai.cloud"
    )
    delayed_en = (
        "Observational status feed with delay and abstraction — not real-time trading execution. "
        "No guaranteed returns or hit-rate claims. Public board: jemaai.cloud"
    )

    pinned_mkm_ko = (
        f"{MKM_DISC}\n\n"
        "· 관측·페이싱 참고용 — 매수·매도·목표가·적중률 방송 없음\n"
        "· 공개 관측 보드: https://jemaai.cloud\n"
        "· 원퀘스천: https://mkmlife.com\n"
        "· B2B·압축 API: https://jema-ai.com (상담 별도)"
    )
    pinned_mkm_en = (
        f"{mkm_core_en}\n\n"
        "· Observational pacing only — no buy/sell, targets, or performance % on air\n"
        "· Public board: https://jemaai.cloud\n"
        "· One-question report: https://mkmlife.com\n"
        "· B2B / compression API: https://jema-ai.com"
    )

    pinned_tkm_ko = (
        f"{TKM_DISC}\n\n"
        "· 전통 리듬·생활 습관 참고용 — 진료·처방·완치 아님\n"
        "· https://mkmlife.com"
    )
    pinned_tkm_en = (
        "Not medical care or diagnosis. Rhythm and habit pacing for reference only.\n"
        "· https://mkmlife.com"
    )

    live_desc_zone_a_ko = (
        "MKM Oracle Sphere — 24시간 ambient 라이브\n"
        "자작 BGM + 정적 비주얼 + 주기적 면책 자막. 실시간 DJ·AI 대화 없음.\n\n"
        f"면책: {MKM_DISC}\n\n"
        f"{delayed_ko}\n\n"
        "더 읽기: jemaai.cloud · mkmlife.com · jema-ai.com"
    )
    live_desc_zone_a_en = (
        "MKM Oracle Sphere — 24h ambient live\n"
        "Self-generated BGM, idle visual, periodic disclaimer burn-in. No live DJ or AI chat.\n\n"
        f"Disclaimer: {mkm_core_en}\n\n"
        f"{delayed_en}\n\n"
        "Learn more: jemaai.cloud · mkmlife.com · jema-ai.com"
    )

    community_go_live_ko = (
        "MKM Field Radio 24h ambient가 시작되었습니다. "
        "투자·의료·법률 자문이 아니며, 관측·페이싱 참고용입니다. "
        "공개 관측: jemaai.cloud"
    )

    burn_ko_short = "참고용·비투자자문 | 지연 관측 | jemaai.cloud"
    burn_en_short = "Observational only | Not advice | Delayed feed"

    checklist: List[str] = [
        "1. preview: reports/video/zone_a_local_preview_latest.mp4 (visual signoff)",
        "2. quality: py scripts/run_ambient_stream_quality_audit_v1.py --write-preview",
        "3. smoke: py scripts/run_ambient_stream_rtmp_smoke_v1.py --seconds 30",
        "4. Studio → 라이브 → 제목/설명: reports/radio_youtube_studio_paste_latest.txt (zone_a blocks)",
        "5. Studio → 고정 댓글: guard_copy pinned_comment_mkm (this JSON)",
        "6. RTMP: User env YOUTUBE_RTMP_URL only — never paste key in chat",
        "7. GoLive: pwsh -File scripts/Invoke-ZoneALiveBroadcastPrep_v1.ps1 -SkipContentRefresh -GoLive",
        "8. NEVER: prices, balances, UID, hit-rate %, live-trading GO, compression KPI headlines",
    ]

    return {
        "schema": "radio_op31c_guard_copy_v1",
        "generated_at_utc": _utc_now(),
        "public_facing_version": PUBLIC_FACING_VERSION,
        "operational_posture": {
            "gtm_lane": "Track C trust / observability demo — not primary revenue (a-codeai B2B, OpenData P0 first)",
            "go_live_default": "hold_until_marketing_focus — T-1 ready (prep + L3 smoke done)",
            "zone_a": "24h ambient — offline Remotion MP4 loop + ffmpeg RTMP (no Node on air)",
            "zone_b": "gated pre-script slots only — gate_ok_* before upload",
        },
        "disclaimers": {
            "mkm_core": _b(mkm_core_ko, mkm_core_en),
            "delayed_observability": _b(delayed_ko, delayed_en),
            "tkm_wellness": _b(TKM_DISC, "Not medical advice. Visit a clinician for symptoms."),
        },
        "studio_paste_blocks": {
            "pinned_comment_mkm": _b(pinned_mkm_ko, pinned_mkm_en),
            "pinned_comment_tkm": _b(pinned_tkm_ko, pinned_tkm_en),
            "live_description_zone_a_ko": live_desc_zone_a_ko,
            "live_description_zone_a_en": live_desc_zone_a_en,
            "community_post_go_live_ko": community_go_live_ko,
            "studio_go_live_checklist": checklist,
        },
        "burn_in_caption": {"ko_short": burn_ko_short, "en_short": burn_en_short},
        "cta_links": [
            {
                "label_ko": "공개 관측 보드",
                "label_en": "Public observability board",
                "url": "https://jemaai.cloud",
                "role": "jemaai_showroom",
            },
            {
                "label_ko": "원퀘스천 리포트",
                "label_en": "One-question report",
                "url": "https://mkmlife.com",
                "role": "mkmlife_b2c",
            },
            {
                "label_ko": "B2B·압축 API",
                "label_en": "B2B compression API",
                "url": "https://jema-ai.com",
                "role": "jema_ai_hub",
            },
        ],
        "never_publish": [
            "실매매 주문·Track A GO·aroon_v1 트리거 대표",
            "적중률·압축률·47.5% 등 내부 벤치 KPI",
            "잔고·UID·API 키·웹훅·내부 호스트",
            "성경·로고스 렌즈의 가격 단정·[NON_GATING] 생략",
            "완벽 방송·환각 제로·실시간 AI 토크 약속",
            "신경과학 증명·수익 보장·양자역학 입증류",
        ],
        "ssot_pointers": {
            "channel_copy": "docs/final/artifacts/radio_youtube_channel_copy_v1_latest.json",
            "studio_paste": "reports/radio_youtube_studio_paste_latest.txt",
            "public_facing": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            "commander_map": "docs/final/MKM_COMMANDER_PLAIN_LANGUAGE_SYSTEM_MAP_V1.md §7",
            "domain_cta": "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md §1.1b",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build O-P31c guard copy JSON (KO/EN).")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    doc = build_guard_copy()
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
