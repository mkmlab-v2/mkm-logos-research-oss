#!/usr/bin/env python3
"""Build customer-masked WTT session stub template (20 rows, NOT real customer) [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"
META_OUT = ROOT / "reports/wtt_customer_masked_stub_build_v1_latest.json"

SESSIONS: list[dict[str, Any]] = [
    {
        "session_id": "stub_cs_refund_01",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "[masked] 주문 ███ 환불 가능한지 문의드립니다."},
            {"role": "user", "text": "이*민 고객명으로 결제 확인 부탁드려요. 010-****-5678 연락 가능합니다."},
        ],
    },
    {
        "session_id": "stub_cs_billing_02",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "[masked] 청구서 ███ 에 중복 결제가 있는 것 같습니다."},
        ],
    },
    {
        "session_id": "stub_wellness_mood_03",
        "domain_tag": "digital-wellness",
        "turns": [
            {"role": "user", "text": "요즘 기분이 가라앉아서 대화를 나누고 싶어요."},
            {"role": "user", "text": "너무 자극적인 말은 피해주세요."},
        ],
    },
    {
        "session_id": "stub_edu_homework_04",
        "domain_tag": "edutech-tutor",
        "turns": [
            {"role": "user", "text": "수학 숙제 힌트만 주실 수 있을까요? 정답은 직접 풀게요."},
        ],
    },
    {
        "session_id": "stub_dev_api_05",
        "domain_tag": "developer-support",
        "turns": [
            {"role": "user", "text": "API 키 sk-*** 마스킹했습니다. /v1/persona 429 오류가 납니다."},
        ],
    },
    {
        "session_id": "stub_b2b_eval_06",
        "domain_tag": "b2b-evaluation",
        "turns": [
            {"role": "user", "text": "30일 파일럿 견적과 데이터 보관 정책을 알고 싶습니다."},
            {"role": "user", "text": "담당자 박*수 명함 받았습니다."},
        ],
    },
    {
        "session_id": "stub_cs_delivery_07",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "[masked] 배송 ███ 아직 미도착입니다. 확인 부탁드립니다."},
        ],
    },
    {
        "session_id": "stub_wellness_sleep_08",
        "domain_tag": "digital-wellness",
        "turns": [
            {"role": "user", "text": "잠이 잘 안 와서 호흡 가이드 짧게 안내해 주세요."},
        ],
    },
    {
        "session_id": "stub_edu_exam_09",
        "domain_tag": "edutech-tutor",
        "turns": [
            {"role": "user", "text": "시험 전에 개념만 정리해 주세요. 범위는 ███ 단원입니다."},
        ],
    },
    {
        "session_id": "stub_cs_account_10",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "계정 ███ 로그인이 안 됩니다. a***@example.com 등록 메일입니다."},
        ],
    },
    {
        "session_id": "stub_wellness_anxiety_11",
        "domain_tag": "digital-wellness",
        "turns": [
            {"role": "user", "text": "불안할 때 쓸 만한 짧은 문구를 추천해 주세요."},
        ],
    },
    {
        "session_id": "stub_b2b_security_12",
        "domain_tag": "b2b-evaluation",
        "turns": [
            {"role": "user", "text": "로그 마스킹 정책과 감사 trail 보존 기간이 궁금합니다."},
        ],
    },
    {
        "session_id": "stub_cs_subscription_13",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "구독 해지 후 ███ 까지 이용 가능한지 확인해 주세요."},
        ],
    },
    {
        "session_id": "stub_dev_webhook_14",
        "domain_tag": "developer-support",
        "turns": [
            {"role": "user", "text": "웹훅 ███ 엔드포인트 500 에러 로그 첨부했습니다(토큰 제거)."},
        ],
    },
    {
        "session_id": "stub_wellness_journal_15",
        "domain_tag": "digital-wellness",
        "turns": [
            {"role": "user", "text": "오늘 일기를 짧게 정리하고 싶어요. 판단하지 말고 들어주세요."},
        ],
    },
    {
        "session_id": "stub_edu_feedback_16",
        "domain_tag": "edutech-tutor",
        "turns": [
            {"role": "user", "text": "제 풀이 ███ 가 맞는지 피드백만 주세요."},
        ],
    },
    {
        "session_id": "stub_cs_warranty_17",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "제품 ███ 보증 기간이 언제까지인지 알려주세요."},
        ],
    },
    {
        "session_id": "stub_b2b_pricing_18",
        "domain_tag": "b2b-evaluation",
        "turns": [
            {"role": "user", "text": "좌석 50명 기준 월 요금과 파일럿 할인 조건이 있나요?"},
        ],
    },
    {
        "session_id": "stub_wellness_calm_19",
        "domain_tag": "digital-wellness",
        "turns": [
            {"role": "user", "text": "오늘은 조용한 톤으로 3문장만 대화하고 싶어요."},
        ],
    },
    {
        "session_id": "stub_cs_escalation_20",
        "domain_tag": "customer-support-chat",
        "turns": [
            {"role": "user", "text": "이전 상담 ███ 티켓이 해결되지 않아 재문의합니다."},
            {"role": "user", "text": "최*우 매니저에게 전달 부탁드립니다. 010-****-4321 콜백 요청."},
        ],
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_rows(*, count: int | None = None) -> list[dict[str, Any]]:
    base = SESSIONS if count is None else SESSIONS[:count]
    rows: list[dict[str, Any]] = []
    for raw in base:
        rows.append(
            {
                "session_id": raw["session_id"],
                "domain_tag": raw.get("domain_tag", "customer-support-chat"),
                "labels": [
                    "masked",
                    "not_customer_data",
                    "synthetic_stub",
                    "pilot_template",
                    "research_only",
                ],
                "customer_provided": False,
                "synthetic_spicy": False,
                "turns": raw["turns"],
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sessions", type=int, default=20)
    ap.add_argument("--meta-out", type=Path, default=META_OUT)
    args = ap.parse_args()

    rows = build_rows(count=min(args.sessions, len(SESSIONS)))
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "wtt_customer_masked_stub_build_v1",
        "generated_at_utc": _utc_now(),
        "session_count": len(rows),
        "out_jsonl": str(args.out_jsonl),
        "note_ko": "실고객 형식 리허설용 stub — SEND·대외 증거 불가",
        "intake_one_click": (
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 "
            "-TenantId wtt-customer-stub-v1 -SessionJsonl data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl "
            "-AllowStubTemplate"
        ),
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "sessions": len(rows), "out": str(args.out_jsonl.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
