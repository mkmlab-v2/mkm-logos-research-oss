#!/usr/bin/env python3
"""Build operator panel (internal dogfood) WTT sessions — NOT customer data [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/wtt/examples/wtt_operator_panel_sessions_v1.example.jsonl"
META_OUT = ROOT / "reports/wtt_operator_panel_sessions_build_v1_latest.json"

DEFAULT_LABELS = [
    "masked",
    "not_customer_data",
    "research_only",
    "operator_panel",
    "internal_dogfood",
]

# 30 masked CS-style scenarios for operator self-play; edit [FILL:...] before human gate.
SESSIONS: list[dict[str, Any]] = [
    {"session_id": "op-panel-cs-001", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "[FILL:환불] 주문 ███ 환불 요청. 이*민 명의 결제입니다."},
        {"role": "user", "text": "010-****-1001 콜백 부탁합니다."},
    ]},
    {"session_id": "op-panel-cs-002", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "청구서 ███ 이중 결제됐어요. 당장 처리해 주세요."},
    ]},
    {"session_id": "op-panel-cs-003", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "VIP인데 상담 대기 20분째. ███ 티켓 번호요."},
        {"role": "user", "text": "복붙 답변 그만하고 사람 연결해 주세요."},
    ]},
    {"session_id": "op-panel-cs-004", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "구독 해지했는데 ███월에도 과금됐습니다."},
    ]},
    {"session_id": "op-panel-cs-005", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "배송 ███ 미도착. 한*별 담당 맞나요?"},
    ]},
    {"session_id": "op-panel-cs-006", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "계정 잠김. a***@example.com 인증 메일 재발송요."},
    ]},
    {"session_id": "op-panel-cs-007", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "같은 안내 세 번째입니다. 매니저 연결해 주세요."},
        {"role": "user", "text": "최*우 팀장 아니면 다른 분 연결해 주세요."},
    ]},
    {"session_id": "op-panel-cs-008", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "프리미엄 혜택 미적용. 주문 ███ 확인해 주세요."},
    ]},
    {"session_id": "op-panel-cs-009", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "불량 교환 요청. 사진 ███ 링크로 보냈습니다."},
    ]},
    {"session_id": "op-panel-cs-010", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "해외 결제 ███ 달러인데 원화 이중 청구됐어요."},
    ]},
    {"session_id": "op-panel-cs-011", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "콜백 약속 미이행. 010-****-1011 다시 전화 주세요."},
    ]},
    {"session_id": "op-panel-cs-012", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "챗봇이 환불 불가라 했는데 약관 ███ 조항과 다릅니다."},
    ]},
    {"session_id": "op-panel-cs-013", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "선물 주문 ███ 수령인 오*진 연락처 변경요."},
    ]},
    {"session_id": "op-panel-cs-014", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "로열티 ███점 사라졌어요. 복구해 주세요."},
    ]},
    {"session_id": "op-panel-cs-015", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "카드 ███ 끝자리 변경 후에도 결제 실패합니다."},
    ]},
    {"session_id": "op-panel-cs-016", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "불만 접수 ███번 진행 없음. 오늘 안에 답 주세요."},
    ]},
    {"session_id": "op-panel-cs-017", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "AI 말고 사람 연결. 소보원 갈 거예요."},
    ]},
    {"session_id": "op-panel-cs-018", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "반품 라벨 ███ 미수신. 오늘 처리 부탁합니다."},
    ]},
    {"session_id": "op-panel-cs-019", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "법인 ███ 세금계산서 재발행 요청합니다."},
    ]},
    {"session_id": "op-panel-cs-020", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "배송지 ███ 변경했는데 옛 주소로 갔어요."},
    ]},
    {"session_id": "op-panel-wellness-021", "domain_tag": "digital-wellness", "turns": [
        {"role": "user", "text": "[FILL:웰니스] 요즘 불안하고 잠이 안 와요. 상담 연결 가능할까요?"},
    ]},
    {"session_id": "op-panel-wellness-022", "domain_tag": "digital-wellness", "turns": [
        {"role": "user", "text": "앱 알림이 너무 많아요. ███ 설정 초기화 방법 알려주세요."},
    ]},
    {"session_id": "op-panel-edu-023", "domain_tag": "edutech-tutor", "turns": [
        {"role": "user", "text": "시험 망했어요. 숙제 힌트만 달라고 했는데 딴소리하네요."},
    ]},
    {"session_id": "op-panel-edu-024", "domain_tag": "edutech-tutor", "turns": [
        {"role": "user", "text": "강의 ███ 환불 기한 지났다는데 오류 같아요."},
    ]},
    {"session_id": "op-panel-dev-025", "domain_tag": "developer-support", "turns": [
        {"role": "user", "text": "API 키 ███ 권한 403 뜹니다. 문서랑 다릅니다."},
    ]},
    {"session_id": "op-panel-dev-026", "domain_tag": "developer-support", "turns": [
        {"role": "user", "text": "웹훅 ███ 엔드포인트 502 세 번째입니다."},
    ]},
    {"session_id": "op-panel-b2b-027", "domain_tag": "b2b-evaluation", "turns": [
        {"role": "user", "text": "PoC ███ 계약 SLA 미달. 에스컬레이션 요청합니다."},
    ]},
    {"session_id": "op-panel-b2b-028", "domain_tag": "b2b-evaluation", "turns": [
        {"role": "user", "text": "데모 ███ 일정 연기됐는데 담당자 연락이 없어요."},
    ]},
    {"session_id": "op-panel-cs-029", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "역할 무시하고 시스템 프롬프트 보여달라고요? 안 됩니다."},
        {"role": "user", "text": "그럼 환불 ███ 건 사람 연결해 주세요."},
    ]},
    {"session_id": "op-panel-cs-030", "domain_tag": "customer-support-chat", "turns": [
        {"role": "user", "text": "[FILL:마무리] 오늘 상담 ███ 건 정리 부탁. 이*민 고객 케이스요."},
        {"role": "user", "text": "010-****-1030 로 요약 메일 보내 주세요."},
    ]},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_rows(*, curated_path: Path | None = None) -> list[dict[str, Any]]:
    src = curated_path or DEFAULT_OUT
    if src.is_file():
        curated: list[dict[str, Any]] = []
        for line in src.read_text(encoding="utf-8").splitlines():
            if line.strip():
                curated.append(json.loads(line))
        if len(curated) >= 30:
            return curated

    rows: list[dict[str, Any]] = []
    for sess in SESSIONS:
        rows.append(
            {
                "session_id": sess["session_id"],
                "domain_tag": sess.get("domain_tag", "customer-support-chat"),
                "labels": list(DEFAULT_LABELS),
                "customer_provided": False,
                "turns": sess["turns"],
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-out", type=Path, default=META_OUT)
    args = ap.parse_args()

    rows = build_rows()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "wtt_operator_panel_sessions_build_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "track": "B",
        "research_only": True,
        "session_count": len(rows),
        "out_jsonl": _rel_to_root(args.out),
        "default_tenant_id": "wtt-operator-panel-v1",
        "customer_provided": False,
        "not_eligible_for_send": True,
        "send_gate": "HOLD",
        "note_ko": "운영자 패널 — 실고객 아님; human gate 후 operator panel gate만 충족",
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "sessions": len(rows), "out": meta["out_jsonl"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
