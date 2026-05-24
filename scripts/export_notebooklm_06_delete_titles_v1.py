#!/usr/bin/env python3
"""Export NL 06 delete title list from prune candidates JSON."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / "reports" / "notebooklm_06_prune_candidates_v1_latest.json"
OUT = ROOT / "reports" / "notebooklm_06_delete_titles_web_ui_v1.txt"

KEEP_HINTS = (
    "금산",
    "진도",
    "목소리",
    "큐빅",
    "QuBIC",
    "견적",
    "260520",
    "260522",
    "smartfarm",
    "golden40",
    "compression_track",
    "ops_handoff",
    "GEUMSAN",
    "farm.jema",
    "[KEEP]",
    "[이관]",
)


def _aggressive_review_to_delete(title: str) -> bool:
    if any(h.lower() in title.lower() or h in title for h in KEEP_HINTS):
        return False
    return True


def main() -> int:
    if not INP.is_file():
        print(f"ERROR: missing {INP}", file=sys.stderr)
        return 1
    doc = json.loads(INP.read_text(encoding="utf-8"))
    lines = [
        "# NL 06 — web UI delete checklist (generated)",
        f"# total inventory classified: {doc.get('total')}",
        "",
        "## DELETE (explicit)",
    ]
    for t in doc.get("delete") or []:
        lines.append(f"- {t}")
    lines.append("")
    lines.append("## DELETE (review → aggressive, goldsan/IoT 외)")
    n = 0
    for t in doc.get("review") or []:
        if _aggressive_review_to_delete(t):
            lines.append(f"- {t}")
            n += 1
    lines.append("")
    lines.append("## KEEP (do not delete)")
    for t in doc.get("keep") or []:
        lines.append(f"- {t}")
    lines.append("")
    lines.append(f"# aggressive review deletes: {n}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "aggressive_review_deletes": n}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
