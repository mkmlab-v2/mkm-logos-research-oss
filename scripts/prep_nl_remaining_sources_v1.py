#!/usr/bin/env python3
"""Prepare remaining NotebookLM text uploads (truncate if needed)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot"
MAX = 120_000

ITEMS = [
    ("nl_upload_central_v1.txt", ROOT / "docs/final/CENTRAL_AGENT_MEMORY_V1.md", "CENTRAL_AGENT_MEMORY_V1.md"),
    (
        "nl_upload_compression_factlock_v1.txt",
        ROOT / "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
        "COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    ),
    (
        "nl_upload_active_report_v1.txt",
        ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
    ),
]


def main() -> int:
    for fname, src, label in ITEMS:
        text = src.read_text(encoding="utf-8")
        truncated = len(text) > MAX
        body = text[:MAX] if truncated else text
        if truncated:
            body += f"\n\n[TRUNCATED at {MAX} chars for NotebookLM upload; full: {label}]\n"
        (OUT / fname).write_text(body, encoding="utf-8")
        print(f"{fname}: {len(text)} -> wrote {len(body)} truncated={truncated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
