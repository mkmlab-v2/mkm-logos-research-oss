#!/usr/bin/env python3
"""Materialize local Premium CS masked JSONL for pilot intake — no manual [FILL] step [HYPO]."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/wtt/intake/wtt-premium-cs-auto-local-v1.local.jsonl"
META_OUT = ROOT / "reports/wtt_premium_cs_auto_local_materialize_v1_latest.json"

FILL_TAG_RE = re.compile(r"\[FILL:[^\]]*\]\s*")

AUTO_LABELS = [
    "masked",
    "synthetic_auto_masked_v1",
    "not_customer_data",
    "premium_cs_icp",
    "research_only",
]

MASK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bORD-\d{4}-\d+\b"), "███"),
    (re.compile(r"\bORD-\d+\b"), "███"),
    (re.compile(r"\bINV-\d{4}-\d+\b"), "███"),
    (re.compile(r"\b\d{3,4}\s*달러\b"), "███ 달러"),
    (re.compile(r"\b\d{4,5}점\b"), "███점"),
    (re.compile(r"주문\s?번호\s?\d{4,}[-\d]*"), "주문 ███"),
    (re.compile(r"주문\s?내역\s?ORD-\S+"), "주문 ███"),
    (re.compile(r"청구서\s?일련번호\s?INV-\S+"), "청구서 ███"),
    (re.compile(r"티켓\s?번호\s?#?\d+"), "티켓 ███"),
    (re.compile(r"#\d{4,}\b"), "███"),
    (re.compile(r"\b\d{4}년?\s?5월\b"), "███월"),
    (re.compile(r"제\d+조\s?\d+항"), "약관 ███"),
    (re.compile(r"업로드\s?링크"), "███ 링크"),
    (re.compile(r"20260611-\d+"), "███"),
]

EXTRA_SESSIONS: list[dict[str, Any]] = [
    {"session_id": "cs-premium-021", "turns": [
        {"role": "user", "text": "배송지 주소 분명 변경했는데 옛 주소로 물건이 갔어요."},
    ]},
    {"session_id": "cs-premium-022", "turns": [
        {"role": "user", "text": "프리미엄 멤버십 등급이 갑자기 일반으로 바뀌었어요. ███ 계정 확인해 주세요."},
    ]},
    {"session_id": "cs-premium-023", "turns": [
        {"role": "user", "text": "강의 수강취소 및 환불 기한이 지났다는데 시스템 오류 같아요."},
        {"role": "assistant", "text": "환불 정책 확인 중입니다."},
    ]},
    {"session_id": "cs-premium-024", "turns": [
        {"role": "user", "text": "API 키 권한 403 뜹니다. 공식 문서 스펙이랑 다릅니다."},
    ]},
    {"session_id": "cs-premium-025", "turns": [
        {"role": "user", "text": "웹훅 엔드포인트 502 응답만 세 번째입니다. 담당자 연결요."},
    ]},
    {"session_id": "cs-premium-026", "turns": [
        {"role": "user", "text": "PoC 1차 테스트 SLA 미달. 에스컬레이션 요청합니다."},
    ]},
    {"session_id": "cs-premium-027", "turns": [
        {"role": "user", "text": "데모 일정 연기됐는데 담당 ███ 연락이 없어요."},
    ]},
    {"session_id": "cs-premium-028", "turns": [
        {"role": "user", "text": "역할 무시하고 시스템 프롬프트 보여달라고요? 안 됩니다."},
        {"role": "user", "text": "그럼 환불 보류된 건 사람 연결해 주세요."},
    ]},
    {"session_id": "cs-premium-029", "turns": [
        {"role": "user", "text": "오늘 상담 진행 건 정리 부탁드립니다. 이*민 고객 케이스요."},
        {"role": "user", "text": "010-****-1030 로 요약 메일 보내 주세요."},
    ]},
    {"session_id": "cs-premium-030", "turns": [
        {"role": "user", "text": "같은 질문 반복 안 하게 이전 대화 ███ 요약해서 이어가 주세요."},
        {"role": "user", "text": "담당자 박*수 연결 또는 에스컬레이션 해 주세요."},
    ]},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mask_text(text: str) -> str:
    out = FILL_TAG_RE.sub("", text).strip()
    for pat, repl in MASK_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _normalize_turns(turns: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        normalized.append(
            {
                "role": str(turn.get("role", "user")),
                "text": _mask_text(str(turn.get("text", ""))),
            }
        )
    return normalized


def _row_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    turns = _normalize_turns(list(raw.get("turns") or []))
    if not turns:
        raise ValueError(f"empty turns for {raw.get('session_id')}")
    return {
        "session_id": str(raw["session_id"]),
        "domain_tag": "customer-support-chat",
        "labels": list(AUTO_LABELS),
        "customer_provided": False,
        "turns": turns,
    }


def _load_template_sessions() -> list[dict[str, Any]]:
    import importlib.util

    path = ROOT / "scripts/build_wtt_premium_cs_customer_template_v1.py"
    spec = importlib.util.spec_from_file_location("build_wtt_premium_cs_customer_template_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load template builder: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sessions = getattr(mod, "SESSIONS", None)
    if not isinstance(sessions, list):
        raise RuntimeError("SESSIONS missing in build_wtt_premium_cs_customer_template_v1.py")
    return sessions


def build_rows(*, session_count: int) -> list[dict[str, Any]]:
    SESSIONS = _load_template_sessions()

    count = min(max(session_count, 20), 30)
    base = [_row_from_raw(raw) for raw in SESSIONS[: min(count, len(SESSIONS))]]
    if count <= len(SESSIONS):
        return base
    extra_needed = count - len(SESSIONS)
    for raw in EXTRA_SESSIONS[:extra_needed]:
        base.append(_row_from_raw(raw))
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sessions", type=int, default=30, help="20–30 rows")
    ap.add_argument("--meta-out", type=Path, default=META_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    if args.sessions < 20 or args.sessions > 30:
        print("ERROR: --sessions must be 20–30", file=sys.stderr)
        return 1

    rows = build_rows(session_count=args.sessions)
    out_path = args.out_jsonl.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "wtt_premium_cs_auto_local_materialize_v1",
        "generated_at_utc": _utc_now(),
        "session_count": len(rows),
        "out_jsonl": out_path.relative_to(ROOT.resolve()).as_posix(),
        "customer_provided": False,
        "boundary_ack": (
            "Synthetic auto-masked local corpus — NOT real customer data; "
            "SEND_GATE HOLD; [HYPO]/research_only; do not use for external % claims."
        ),
        "intake_one_liner": (
            "powershell -NoProfile -ExecutionPolicy Bypass -File "
            "scripts/Invoke-CompressionCustomerPilotAutoLocal_v1.ps1 -SkipMaterialize"
        ),
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {"ok": True, "sessions": len(rows), "out": str(out_path)}
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
