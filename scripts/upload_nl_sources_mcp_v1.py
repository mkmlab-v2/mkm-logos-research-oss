#!/usr/bin/env python3
"""Upload prepared NL text files via notebooklm-mcp HTTP if unavailable use print manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
NOTEBOOK_ID = "mkm-core-intelligence-fact-foc"

UPLOADS = [
    ("Compression Pipeline Fact-Lock (full)", "nl_upload_compression_factlock_v1.txt"),
    ("CENTRAL_AGENT_MEMORY part 1/3", "nl_chunk_central_0.txt"),
    ("CENTRAL_AGENT_MEMORY part 2/3", "nl_chunk_central_1.txt"),
    ("CENTRAL_AGENT_MEMORY part 3/3", "nl_chunk_central_2.txt"),
    ("ACTIVE_REPORT part 1/4", "nl_chunk_active_report_0.txt"),
    ("ACTIVE_REPORT part 2/4", "nl_chunk_active_report_1.txt"),
    ("ACTIVE_REPORT part 3/4", "nl_chunk_active_report_2.txt"),
    ("ACTIVE_REPORT part 4/4", "nl_chunk_active_report_3.txt"),
]


def main() -> int:
    # Emit JSON lines for parent agent / manual MCP batch (stdlib only).
    for title, fname in UPLOADS:
        path = PILOT / fname
        if not path.is_file():
            print(json.dumps({"error": "missing", "file": fname}), file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        rec = {
            "notebook_id": NOTEBOOK_ID,
            "type": "text",
            "title": title,
            "content_chars": len(text),
            "content": text,
        }
        print(json.dumps(rec, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
