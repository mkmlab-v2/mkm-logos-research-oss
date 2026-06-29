#!/usr/bin/env python3
"""Scan Myeongni golden / interpret SFT JSONL for placeholder or forbidden ganji tokens.

Exit 0 when clean. Exit 1 when violations found (Data-Centric gate before Exact SFT).

Example::

  py scripts/check_myeongri_training_placeholder_purge_v1.py \\
    --input-jsonl data/training/myeongri_deterministic_lora_golden_bulk_v1/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("placeholder_token", re.compile(r"\bPLACEHOLDER\b", re.I)),
    ("mustache_placeholder", re.compile(r"\{\{[^}]+\}\}")),
    ("english_gan_ji", re.compile(r"\b(Gan|Ji|Xu|Ren|Zi|Chou|Yin|Mao)\b")),
    ("latin_single_pillar", re.compile(r'"year"\s*:\s*"[A-Za-z]{1,3}"')),
    ("todo_marker", re.compile(r"\b(TODO|FIXME|TBD)\b")),
    ("ellipsis_placeholder", re.compile(r"\.{3,}\s*(ganji|pillar|기둥)", re.I)),
)


def _scan_text(text: str) -> list[str]:
    hits: list[str] = []
    for name, pat in _FORBIDDEN_PATTERNS:
        if pat.search(text):
            hits.append(name)
    return hits


def _row_blob(row: dict) -> str:
    parts = [json.dumps(row, ensure_ascii=False)]
    for key in ("instruction", "output", "expected_result"):
        val = row.get(key)
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, dict):
            parts.append(json.dumps(val, ensure_ascii=False))
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out-json", type=Path, default=ROOT / "reports/myeongri_training_placeholder_purge_v1_latest.json")
    args = ap.parse_args()
    if not args.input_jsonl.is_file():
        print(f"missing input: {args.input_jsonl}", file=sys.stderr)
        return 2

    violations: list[dict] = []
    n = 0
    for i, line in enumerate(args.input_jsonl.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        if args.limit > 0 and n >= args.limit:
            break
        row = json.loads(line)
        n += 1
        hits = _scan_text(_row_blob(row))
        if hits:
            violations.append(
                {
                    "line": i,
                    "sample_id": row.get("sample_id"),
                    "patterns": hits,
                }
            )

    doc = {
        "schema": "myeongri_training_placeholder_purge_v1",
        "input_jsonl": str(args.input_jsonl),
        "rows_scanned": n,
        "violation_count": len(violations),
        "purge_ok": len(violations) == 0,
        "violations": violations[:200],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"purge_ok": doc["purge_ok"], "violation_count": len(violations), "out": str(args.out_json)}))
    return 0 if doc["purge_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
