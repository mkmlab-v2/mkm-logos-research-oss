#!/usr/bin/env python3
"""Emit Track C B2B counsel submission email draft (commander sends — agent does not mail)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
SCAN = ROOT / "reports/track_c_b2b_counsel_copy_scan_v1_latest.json"
MANIFEST = ART / "track_c_b2b_counsel_export_manifest_v1_latest.json"
SIGNOFF = ART / "track_c_b2b_commander_signoff_v1_latest.json"
DEFAULT_OUT = ART / "track_c_b2b_counsel_submission_email_draft_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict[str, Any]:
    scan = _read(SCAN) or {}
    manifest = _read(MANIFEST) or {}
    signoff = _read(SIGNOFF) or {}
    scan_ok = scan.get("scan_ok", False)
    file_count = manifest.get("file_count", "—")
    cmd_ext = signoff.get("ready_for_external_send") is True and signoff.get("scope") == "external_send"
    body = f"""안녕하세요, 법무팀님.

MKM Track C **B2B Two-Layer Agent** (Execution Lock × Meaning Lock) 미팅팩 — 대외 카피·면책 검토 요청드립니다.

첨부: `track_c_b2b_counsel_export_pack_v1.zip` (**{file_count} files**)
포함: Two-Layer 슬라이드·인쇄 HTML·15분 내부 리허설 런북·Logos B2B 슬라이드·레드액션 데모·원페이저·**Compression plugin appendix (billing-mode 표)**·**Long-form spine SLA draft `[HYPO]`**·PUBLIC_FACING v1.7·사업계획 §3.8.1·가드레일 스캔 JSON·쇼룸 PNG 3종

**사전 스캔 (AI, 법적 승인 아님):** copy_scan={"PASS" if scan_ok else "FAIL — 첨부 전 확인"}
**현재 상태:** manifest DRAFT_AUTO · Logos [NON_GATING] · commander external_send signoff={"recorded" if cmd_ext else "not on file"}

확인 요청 (5분):
1. 투자·거래 조언·면책 문구 (CTO/CISO 미팅 자료)
2. OEM 파트너십 [HYPO] — 과도한 확약 여부
3. 슬라이드 헤드라인에 Track A %·무손실·실매매 자동 승격 **없음** (FAIL-COMP-004)
4. **Billing-mode 분리:** Track A 47.5% ≠ NG spine/MKVS — 장문 MKVS bench는 별도 SLA 초안(Step 9)이며 ACTIVE 승격 근거 아님
5. 와이어 envelope ≠ compression KPI (미팅팩 인덱스 경고 정합)
6. external send 승격 전 필수 조건 (법무 회신 + `record_track_c_b2b_legal_counsel_signoff_v1.py`)

본 팩은 **내부 리허설 완료** 전제이며, AI는 법무 서명을 대체할 수 없습니다.
회신 티켓/이메일 ID는 `record_track_c_b2b_legal_counsel_signoff_v1.py --counsel-reference` 로 기록 예정입니다.

감사합니다.
MKM Ops (INTERNAL)"""
    return {
        "schema": "track_c_b2b_counsel_submission_email_draft_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "lane": "track_c_b2b",
        "send_status": "DRAFT_ONLY_NOT_SENT",
        "ready_for_external_send": False,
        "suggested_subject": "[MKM][Track C] B2B Two-Layer Agent — counsel copy review (5 min pack)",
        "attachment": "track_c_b2b_counsel_export_pack_v1.zip",
        "attachment_file_count": manifest.get("file_count"),
        "commander_external_send_signoff": cmd_ext,
        "body_ko": body,
        "boundary_ack": "Agent cannot send mail; commander sends from org mailbox.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
