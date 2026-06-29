#!/usr/bin/env python3
"""Emit CTO/CISO outreach email draft after external_send gate is true (commander sends)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
READINESS = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
SIGNOFF = ART / "track_c_b2b_legal_counsel_signoff_v1_latest.json"
DEFAULT_OUT = ART / "track_c_b2b_external_cto_email_draft_v1_latest.json"
PDF_DEFAULT = ART / "track_c_b2b_two_layer_agent_slide_v1_latest.pdf"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build(*, pdf_path: Path, company: str, contact: str) -> dict[str, Any]:
    readiness = _read(READINESS)
    signoff = _read(SIGNOFF)
    if not readiness.get("ready_for_external_send"):
        raise RuntimeError(
            "ready_for_external_send is false — run signoff + readiness check first"
        )
    pdf_rel = (
        pdf_path.relative_to(ROOT).as_posix()
        if pdf_path.is_file()
        else pdf_path.relative_to(ROOT).as_posix()
        if pdf_path.is_absolute() and ROOT in pdf_path.parents
        else pdf_path.as_posix()
    )
    pdf_name = Path(pdf_rel).name
    body = f"""안녕하세요, {contact}님.

{company} 측 엔터프라이즈 AI 거버넌스 관련해, MKM Track C **Two-Layer Agent**(Execution Lock × Meaning Lock) 개념 1장을 공유드립니다.

첨부: `{pdf_name}` (1-page overview)
· 실행 경계(CISO) + 의미·비용 게이트(CTO/FinOps)를 분리한 **OEM형 플러그인** 개념
· 투자 권유·매매 지시·수익 보장 없음 · Logos 레이어 [NON_GATING]
· 통합·OEM·납품은 **서면 합의·PoC 완료 후**에만 논의 ([HYPO])

20분 화상 미팅 가능하시면 편한 시간 알려주시면 감사하겠습니다.

감사합니다.
[보내는이 · 회사명]"""
    return {
        "schema": "track_c_b2b_external_cto_email_draft_v1",
        "generated_at_utc": _utc_now(),
        "classification": "EXTERNAL_DRAFT",
        "lane": "track_c_b2b",
        "send_status": "DRAFT_ONLY_NOT_SENT",
        "ready_for_external_send": True,
        "readiness_ref": READINESS.relative_to(ROOT).as_posix(),
        "signoff_ref": SIGNOFF.relative_to(ROOT).as_posix() if SIGNOFF.is_file() else None,
        "counsel_reference": signoff.get("counsel_reference"),
        "suggested_subject": f"[MKM] Enterprise AI governance — Two-Layer Agent overview ({company})",
        "attachment_pdf": pdf_rel,
        "attachment_pdf_exists": pdf_path.is_file(),
        "placeholders": {"company": company, "contact": contact},
        "body_ko": body,
        "boundary_ack": "Agent cannot send mail; commander sends manually. No % headlines or live-trading claims.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pdf-path", type=Path, default=PDF_DEFAULT)
    ap.add_argument("--company", default="[회사명]")
    ap.add_argument("--contact", default="[담당자명]")
    args = ap.parse_args()
    doc = build(pdf_path=args.pdf_path, company=args.company, contact=args.contact)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out_json),
                "pdf_exists": doc["attachment_pdf_exists"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
