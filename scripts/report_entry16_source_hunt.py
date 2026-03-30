#!/usr/bin/env python3
"""Generate a compact summary report for ENTRY_16 source-hunt JSONL."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_log.jsonl"
OUT = ROOT / "docs" / "final" / "artifacts" / "entry16_source_hunt_summary.json"


def iter_rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            yield json.loads(s)


def main() -> int:
    rows = list(iter_rows(SRC))
    conf = Counter(str(r.get("confidence", "")).strip() for r in rows)
    witness = Counter(str(r.get("ezra_2_54_direct_witness", "")).strip() for r in rows)
    modes = Counter(str(r.get("access_mode", "")).strip() for r in rows)

    summary = {
        "schema": "entry16_source_hunt_summary_v1",
        "source_log": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "total_sources": len(rows),
        "confidence_counts": dict(conf),
        "witness_counts": dict(witness),
        "access_mode_counts": dict(modes),
        "has_direct_witness": witness.get("yes", 0) > 0,
        "next_gate": (
            "promote_entry16_candidate"
            if witness.get("yes", 0) > 0
            else "keep_missing_anchor_until_source_update"
        ),
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
