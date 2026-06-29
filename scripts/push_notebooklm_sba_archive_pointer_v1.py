#!/usr/bin/env python3
"""Add SBA 2026 archive pointer snippet to 99_ARCHIVE_MKM notebook (nlm)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NB = "9d463afb-328a-4496-b348-a65ca62bd8f7"
SBA_NB = "b25977f3-1f92-4075-8dfe-d4074ca708a7"
TITLE = "SBA_2026_ARCHIVE_POINTER_v1"
OUT = ROOT / "reports" / "notebooklm_sba_archive_pointer_push_v1_latest.json"

TEXT = """# SBA 2026 모두의 챌린지 — 아카이브 포인터 (read-only)

- **상태:** 이벤트 종료 (2026-05-12). 운영·Track A·실매매 GO 근거로 사용 금지.
- **레거시 노트북:** https://notebooklm.google.com/notebook/b25977f3-1f92-4075-8dfe-d4074ca708a7
- **활성 허브:** 99_ARCHIVE_MKM_2026Q2 (본 소스)
- **Fact-Lock:** 구현·게이트는 CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md + scripts + exit code만 SSOT.
- **LG HS 발표 자료:** 필요 시 레거시 SBA 노트에서만 조회; 신규 승격 주장 금지.
"""


def _titles(notebook_id: str) -> set[str]:
    raw = subprocess.check_output(
        ["nlm", "notebook", "get", notebook_id, "--json"],
        text=True,
        encoding="utf-8-sig",
    )
    data = json.loads(raw)
    val = data.get("value", data)
    return {s.get("title", "") for s in (val.get("sources") or [])}


def main() -> int:
    existing = _titles(ARCHIVE_NB)
    if TITLE in existing:
        doc = {"schema": "notebooklm_sba_archive_pointer_push_v1", "status": "skipped_exists", "title": TITLE}
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False))
        return 0

    r = subprocess.run(
        ["nlm", "source", "add", ARCHIVE_NB, "--text", TEXT, "--title", TITLE, "--wait"],
        capture_output=True,
        text=True,
    )
    doc = {
        "schema": "notebooklm_sba_archive_pointer_push_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "archive_notebook_id": ARCHIVE_NB,
        "sba_legacy_notebook_id": SBA_NB,
        "title": TITLE,
        "exit_code": r.returncode,
        "stderr": (r.stderr or "")[-500:],
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
