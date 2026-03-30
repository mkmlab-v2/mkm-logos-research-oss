#!/usr/bin/env python3
"""Filter DSS enriched rows to canonical-like textual content only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IN_PATH = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched.jsonl"
OUT_PATH = ROOT / "data" / "logos" / "manuscripts" / "dss_parsed_enriched_canonical_only.jsonl"
REPORT = ROOT / "reports" / "constitution" / "btrack_pilot" / "dss_canonical_filter_report_latest.json"


ALLOW_DOC_HINTS = (
    "btrack_dss_1qm",
    "btrack_dss_1qs",
    "btrack_dss_deut",
)
DENY_DOC_HINTS = (
    "checklist",
    "closeout",
    "bundle_note",
)
DENY_TEXT_HINTS = (
    "workflow",
    "run id",
    "skipbundle",
    "frontline",
    "promotion gate",
    "pytest",
    "ci",
    "generated",
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _accept(row: dict[str, Any]) -> bool:
    doc = str(row.get("source_doc", "")).lower()
    text = str(row.get("text", "")).lower()
    if any(k in doc for k in DENY_DOC_HINTS):
        return False
    if any(k in text for k in DENY_TEXT_HINTS):
        return False
    if any(k in doc for k in ALLOW_DOC_HINTS):
        return True
    # Fallback: keep rows that look like translated textual lines.
    if len(text.split()) >= 6 and not text.startswith("[") and "|" not in text:
        return True
    return False


def main() -> int:
    rows = _load_jsonl(IN_PATH)
    kept = [r for r in rows if _accept(r)]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    rep = {
        "schema": "dss_canonical_filter_report_v1",
        "input_rows": len(rows),
        "kept_rows": len(kept),
        "output_path": str(OUT_PATH),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_PATH}")
    print(f"WROTE: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
