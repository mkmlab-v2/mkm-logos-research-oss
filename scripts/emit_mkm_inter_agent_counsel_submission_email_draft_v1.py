#!/usr/bin/env python3
"""Emit internal email/ticket draft for counsel submission (does not send mail)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_counsel_submission_email_draft_latest.json"
ZIP_META = ROOT / "docs/final/artifacts/mkm_inter_agent_counsel_zip_pack_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build() -> dict:
    zip_name = "mkm_inter_agent_counsel_export_pack_v1.zip"
    if ZIP_META.is_file():
        meta = json.loads(ZIP_META.read_text(encoding="utf-8"))
        zip_name = Path(str(meta.get("zip_path") or zip_name)).name

    body_ko = f"""안녕하세요, 법무팀님.

MKM Inter-Agent Encoding(RQ-019) 대외 카피·면책 검토 요청드립니다.

첨부: {zip_name} (manifest 기준 16개 파일 + 인덱스)
동봉 요지:
- mkm_inter_agent_ir_snippet_v1.md (대외 초안 KO/EN — 법무 수정 전 송부 금지)
- PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md v1.7

확인 요청:
1. Lingua Franca 완성·업계 표준 채택·상용 SLA·100% 무손실 복원 주장 없음
2. Track A 동결 벤치(~47% token saving)와 기계 왕복·L1 human decode(~58%, research_only) 혼동 금지 문구
3. 수정된 KO/EN 한 줄 승인 또는 redline

회신 시 티켓/이메일 ID를 기록해 주시면 record_mkm_inter_agent_legal_counsel_signoff_v1.py에 반영합니다.

감사합니다.
MKM Ops (INTERNAL)
"""

    body_en = """Legal review request: MKM RQ-019 inter-agent encoding external copy.

Attached ZIP per counsel export manifest. Please review IR snippet + PUBLIC_FACING v1.7 alignment.
Do not approve claims of finished lingua franca, production SLA, lossless decode, or SOTA superiority.
Reply with ticket/email ID for our sign-off recorder.

Thank you."""

    return {
        "schema": "mkm_inter_agent_counsel_submission_email_draft_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "send_status": "DRAFT_ONLY_NOT_SENT",
        "suggested_subject": "[MKM][RQ-019] Inter-Agent Encoding — external copy legal review",
        "attachment": zip_name,
        "body_ko": body_ko.strip(),
        "body_en": body_en.strip(),
        "boundary_ack": "Agent cannot send email; commander sends from org mailbox and records counsel reference.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json), "send_status": doc["send_status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
