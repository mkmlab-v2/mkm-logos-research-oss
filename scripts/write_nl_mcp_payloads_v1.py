#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
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
for i, (title, fname) in enumerate(UPLOADS):
    text = (PILOT / fname).read_text(encoding="utf-8")
    (PILOT / f"nl_mcp_payload_{i}.json").write_text(
        json.dumps({"title": title, "content": text, "notebook_id": "mkm-core-intelligence-fact-foc"}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(i, title, len(text))
