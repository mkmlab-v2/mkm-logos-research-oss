#!/usr/bin/env python3
"""Build KEEP/DELETE candidate lists for NL notebook 06 from title inventory.

Input: reports/notebooklm_06_source_titles_raw_v1.txt (one title per line)
Output: reports/notebooklm_06_prune_candidates_v1_latest.json
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "notebooklm_06_source_titles_raw_v1.txt"
OUT = ROOT / "reports" / "notebooklm_06_prune_candidates_v1_latest.json"

KEEP_SUBSTRINGS = [
    "smartfarm_geumsan",
    "golden40",
    "compression_track_a",
    "GEUMSAN_IOT",
    "00_ops_handoff",
    "farm.jema-ai.com/smartfarm",
    "revision_email",
    "gonogo",
    "vendor_rfq",
    "vendor_outreach",
    "autopilot_brief",
    "QuBics",
    "견적",
    "목소리",
    "큐빅",
    "qubics",
]

DELETE_KEYWORDS = [
    "LG",
    "압축",
    "compression",
    "Golden 40",
    "예언",
    "prophecy",
    "LOGOS",
    "Track C",
    "MASTER",
    "OPS_COMMAND",
    "명리",
    "만세력",
    "SBA",
    "붙여넣은 텍스트",
    "MS RQ",
    "defense",
    "oracle_v",
    "inter-agent",
]


def _load_titles() -> list[str]:
    if not RAW.is_file():
        return []
    lines = []
    for line in RAW.read_text(encoding="utf-8", errors="replace").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        lines.append(t)
    return lines


def _classify(title: str) -> str:
    low = title.lower()
    for k in KEEP_SUBSTRINGS:
        if k.lower() in low or k in title:
            return "keep"
    for k in DELETE_KEYWORDS:
        if k.lower() in low or k in title:
            return "delete"
    if title.startswith("[KEEP]") or "[KEEP]" in title:
        return "keep"
    if title.startswith("[HOLD]") or title.startswith("[이관]"):
        return "review"
    return "review"


def main() -> int:
    titles = _load_titles()
    if not titles:
        print(json.dumps({"error": "no titles", "hint": f"populate {RAW}"}), file=sys.stderr)
        return 1
    buckets: dict[str, list[str]] = {"keep": [], "delete": [], "review": []}
    for t in titles:
        buckets[_classify(t)].append(t)
    doc = {
        "schema": "notebooklm_06_prune_candidates_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notebook_id": "06-2026q2",
        "total": len(titles),
        "counts": {k: len(v) for k, v in buckets.items()},
        "keep": buckets["keep"],
        "delete": buckets["delete"],
        "review": buckets["review"],
        "note": "MCP/nlm cannot bulk-delete; use web UI or nlm source delete after login.",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "counts": doc["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
