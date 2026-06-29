#!/usr/bin/env python3
"""Emit Logos GTM counsel submission email draft (commander sends — agent does not mail)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
BUNDLE = ROOT / "reports/logos_gtm_counsel_handoff_bundle_v1_latest.json"
MANIFEST = ART / "logos_gtm_counsel_export_manifest_v1_latest.json"
SIGNOFF = ART / "logos_track_l_external_send_signoff_v1_latest.json"
DEFAULT_OUT = ART / "logos_gtm_counsel_submission_email_draft_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    bundle = _read(BUNDLE)
    manifest = _read(MANIFEST)
    signoff = _read(SIGNOFF)
    scans_ok = all(
        s.get("ok") for s in (bundle.get("scan_steps") or []) if isinstance(s, dict)
    )
    counsel_present = bool((signoff.get("legal_counsel_signoff") or {}).get("present"))
    file_count = manifest.get("file_count", "—")
    body = f"""안녕하세요, 법무팀님.

MKM **Logos Graph Studio** — B-track Scripture **research demo** 공개 카피·면책 검토 요청드립니다.

**포함 파일 ({file_count}):** `logos_gtm_counsel_export_manifest_v1_latest.json` 목록 참조
- Counsel handoff brief · GTM LinkedIn variants · organic 1:1 outreach 초안
- Public docs/glossary copy scan JSON · signoff worksheet (template)
- PUBLIC_FACING v1.7 체크리스트

**Live surfaces (검토 대상 URL):**
- Demo: {bundle.get('public_surfaces', {}).get('demo_primary_url', '—')}
- Workspace: {bundle.get('public_surfaces', {}).get('workspace_url', '—')}
- Docs: {bundle.get('public_surfaces', {}).get('public_docs_url', '—')}

**사전 스캔 (AI, 법적 승인 아님):** copy_scans={"PASS" if scans_ok else "FAIL — 첨부 전 확인"}
**현재 상태:** send_gate=HOLD · Logos [NON_GATING] · counsel_signoff={"present" if counsel_present else "pending"}

확인 요청:
1. 투자·거래·예언 성능·신학 제품 주장 **없음** (research_only · NON_GATING)
2. thermodynamic alias·Track A KPI 헤드라인 **없음**
3. 1:1 outreach만 허용 — mass SEND·paid ads **금지** 유지
4. 회신 후: `py scripts/record_logos_gtm_legal_counsel_signoff_v1.py --counsel-reference <ticket-id> --apply-signoff`

본 요청은 **대외 SEND 승격 전** 검토이며, AI는 법무 서명을 대체할 수 없습니다.

감사합니다.
MKM Ops (INTERNAL)"""
    return {
        "schema": "logos_gtm_counsel_submission_email_draft_v1",
        "generated_at_utc": _utc(),
        "classification": "INTERNAL_ONLY",
        "lane": "oracle_logos",
        "send_status": "DRAFT_ONLY_NOT_SENT",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "ready_for_counsel_submission": bundle.get("ready_for_counsel_submission", False),
        "suggested_subject": "[MKM][Logos] Graph Studio public copy — counsel review (B-track · HOLD)",
        "manifest": "docs/final/artifacts/logos_gtm_counsel_export_manifest_v1_latest.json",
        "counsel_brief": "docs/final/artifacts/logos_gtm_counsel_handoff_brief_v1_latest.md",
        "body_ko": body,
        "boundary_ack": "Agent cannot send mail; commander sends from org mailbox.",
        "next_record_command": (
            "py scripts/record_logos_gtm_legal_counsel_signoff_v1.py "
            "--counsel-reference <ticket-id> --apply-signoff"
        ),
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
