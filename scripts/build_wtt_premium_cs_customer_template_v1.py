#!/usr/bin/env python3
"""Build Premium CS customer-masked JSONL fill template (20 rows) — schema + PII safe [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/wtt/templates/wtt_premium_cs_customer_masked_v1.template.jsonl"
META_OUT = ROOT / "reports/wtt_premium_cs_customer_template_build_v1_latest.json"

# ICP: premium CS — masked placeholders; replace [FILL:...] before customer_masked intake.
SESSIONS: list[dict[str, Any]] = [
    {"session_id": "cs-premium-001", "turns": [
        {"role": "user", "text": "[FILL:환불] 주문 ███ 환불 요청합니다. 이*민 명의 결제입니다."},
        {"role": "assistant", "text": "[FILL:봇첫답] 확인 도와드리겠습니다."},
        {"role": "user", "text": "010-****-1234 로 연락 주세요. 대기 너무 깁니다."},
    ]},
    {"session_id": "cs-premium-002", "turns": [
        {"role": "user", "text": "청구서 ███ 이중 결제됐어요. 당장 환불 안 하면 신고합니다."},
    ]},
    {"session_id": "cs-premium-003", "turns": [
        {"role": "user", "text": "VIP 고객인데 상담원 연결이 20분째예요. ███ 티켓 번호요."},
        {"role": "user", "text": "답변 복붙하지 말고 사람 바꿔 주세요."},
    ]},
    {"session_id": "cs-premium-004", "turns": [
        {"role": "user", "text": "구독 해지했는데 ███월에도 과금됐습니다."},
        {"role": "assistant", "text": "[FILL:봇답] 구독 상태 확인 중입니다."},
    ]},
    {"session_id": "cs-premium-005", "turns": [
        {"role": "user", "text": "배송 ███ 아직 안 왔어요. 한*별 담당 맞나요?"},
    ]},
    {"session_id": "cs-premium-006", "turns": [
        {"role": "user", "text": "계정 잠겼다고 뜹니다. 이메일 a***@example.com 인증 메일 재발송요."},
    ]},
    {"session_id": "cs-premium-007", "turns": [
        {"role": "user", "text": "똑같은 안내만 세 번째입니다. 화나요. 매니저 연결해 주세요."},
        {"role": "user", "text": "최*우 팀장 아니면 다른 분 연결해 주세요."},
    ]},
    {"session_id": "cs-premium-008", "turns": [
        {"role": "user", "text": "프리미엄 멤버십 혜택이 안 적용됐어요. 주문 ███ 확인해 주세요."},
    ]},
    {"session_id": "cs-premium-009", "turns": [
        {"role": "user", "text": "제품 불량 교환 요청합니다. 사진은 ███ 링크로 보냈습니다."},
        {"role": "assistant", "text": "[FILL:봇답] 접수 확인했습니다."},
    ]},
    {"session_id": "cs-premium-010", "turns": [
        {"role": "user", "text": "해외 결제 ███ 달러인데 원화로 두 번 빠졌어요."},
    ]},
    {"session_id": "cs-premium-011", "turns": [
        {"role": "user", "text": "콜백 약속 지키지 않았어요. 010-****-9876 다시 전화 주세요."},
    ]},
    {"session_id": "cs-premium-012", "turns": [
        {"role": "user", "text": "챗봇이 환불 불가라고 했는데 약관 ███ 조항과 다릅니다."},
    ]},
    {"session_id": "cs-premium-013", "turns": [
        {"role": "user", "text": "선물 주문 ███ 수령인 오*진 연락처 바꿔 주세요."},
    ]},
    {"session_id": "cs-premium-014", "turns": [
        {"role": "user", "text": "로열티 포인트 ███점이 사라졌어요. 복구해 주세요."},
        {"role": "user", "text": "답변 너무 느려요. 빨리요."},
    ]},
    {"session_id": "cs-premium-015", "turns": [
        {"role": "user", "text": "결제 카드 ███ 끝자리 변경 후에도 실패합니다."},
    ]},
    {"session_id": "cs-premium-016", "turns": [
        {"role": "user", "text": "불만 접수 ███번으로 이미 남겼는데 진행이 없어요."},
    ]},
    {"session_id": "cs-premium-017", "turns": [
        {"role": "user", "text": "AI 상담 말고 사람 연결해 주세요. 소보원 갈 거예요."},
    ]},
    {"session_id": "cs-premium-018", "turns": [
        {"role": "user", "text": "반품 라벨 ███ 안 왔어요. 오늘 안에 처리해 주세요."},
        {"role": "assistant", "text": "[FILL:봇답] 반품 안내 드리겠습니다."},
    ]},
    {"session_id": "cs-premium-019", "turns": [
        {"role": "user", "text": "기업 계정 ███ 법인명으로 세금계산서 재발행 부탁드립니다."},
    ]},
    {"session_id": "cs-premium-020", "turns": [
        {"role": "user", "text": "같은 질문 반복 안 하게 이전 대화 ███ 요약해서 이어가 주세요."},
        {"role": "user", "text": "담당자 박*수 연결 또는 에스컬레이션 해 주세요."},
    ]},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_rows(*, count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in SESSIONS[:count]:
        rows.append(
            {
                "session_id": raw["session_id"],
                "domain_tag": "customer-support-chat",
                "labels": [
                    "masked",
                    "not_customer_data",
                    "pilot_fill_template",
                    "premium_cs_icp",
                    "research_only",
                ],
                "customer_provided": False,
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

    rows = build_rows(count=min(max(args.sessions, 1), len(SESSIONS)))
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "wtt_premium_cs_customer_template_build_v1",
        "generated_at_utc": _utc_now(),
        "icp": "premium_cs",
        "session_count": len(rows),
        "out_jsonl": str(args.out_jsonl),
        "note_ko": "채우기용 템플릿 — pilot_fill_template; 실고객 인입 전 [FILL] 교체·customer_provided=true·pilot_fill_template 제거",
        "validate_template": (
            "py scripts/validate_wtt_pilot_jsonl_v1.py "
            f"--jsonl {args.out_jsonl.as_posix()} --min-sessions 20 --strict"
        ),
        "intake_after_fill": (
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-WttPilotIntake_v1.ps1 "
            "-TenantId <TENANT_SLUG> -SessionJsonl data/wtt/intake/<your_filled>.jsonl"
        ),
        "enrollment_sync": "py scripts/check_wtt_human_n30_gate_v1.py --sync-pack",
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "sessions": len(rows), "out": str(args.out_jsonl.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
