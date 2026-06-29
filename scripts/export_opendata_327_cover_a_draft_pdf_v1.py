#!/usr/bin/env python3
"""Export OpenData 327 Part A cover as a DRAFT PDF (replace with K-Startup official form before upload)."""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MERGE_GUIDE = ROOT / "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/opendata_327_part_a_cover_draft_v1.pdf"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cover_md(*, submit_date_kst: str) -> str:
    guide = json.loads(MERGE_GUIDE.read_text(encoding="utf-8-sig"))
    task_id = guide.get("output_target", {}).get("cover_task_id", "①")
    entity = guide.get("legal_entity", "주식회사 목소리네트워크")
    return f"""# AI+ OpenData 챌린지 — 사업계획서 표지 (Part A)

**상태:** DRAFT — 제출 직전 **K-Startup 공고 별첨 표지 PDF**로 교체 필수.

---

## 필수 항목 (병합·접수 전 확인)

| 항목 | 값 |
|------|-----|
| 과제번호 | {task_id} |
| 기업명 | {entity} |
| 대표이사 | 이기륜 |
| 사업자등록번호 | 628-86-01742 |
| 제출일 | {submit_date_kst} |

---

**공고:** 중소벤처기업부 제2026-327호 「AI+ OpenData 챌린지」  
**과제:** ① 정책자금 융자 신청서 자동 생성 (중진공, 계약 연계형)  
**마감:** 2026-06-05 18:00 KST (공고 재확인)

본 PDF는 레포 자동 생성 **초안 표지**이며, K-Startup 온라인 양식과 **픽셀·서식 일치를 보장하지 않습니다**.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--submit-date-kst",
        default="[Human: K-Startup 접수일]",
        help="Cover submit date line (default placeholder until human sets)",
    )
    ap.add_argument("--out-pdf", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    from export_opendata_327_submission_pdf_v1 import _export_part, _find_browser

    md = _cover_md(submit_date_kst=args.submit_date_kst)
    tmp_md = args.out_pdf.with_suffix(".source.md")
    html_out = args.out_pdf.with_suffix(".html")
    tmp_md.parent.mkdir(parents=True, exist_ok=True)
    tmp_md.write_text(md, encoding="utf-8")

    browser = _find_browser()
    part = _export_part(
        browser=browser,
        source_md=tmp_md,
        html_out=html_out,
        pdf_out=args.out_pdf,
        title="OpenData 327 Part A Cover (DRAFT)",
    )
    summary = {
        "schema": "opendata_327_cover_a_draft_export_v1",
        "generated_at_utc": _utc_now(),
        "status": "DRAFT_REPLACE_BEFORE_KSTARTUP_UPLOAD",
        "pdf": part["pdf"],
        "size_kb": part["size_kb"],
        "boundary_ack": "Official K-Startup cover form must replace this draft before portal upload.",
    }
    out_json = ROOT / "reports/opendata_327_cover_a_draft_export_latest.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "pdf": part["pdf"], "summary": str(out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
