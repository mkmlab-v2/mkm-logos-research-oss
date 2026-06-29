#!/usr/bin/env python3
"""Merge public-safe corpora for proof-sprint PoC (golden40 + open structured)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/stateless_poc_proof_sprint_composite_v1.jsonl"
SOURCES = [
    (ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl", "golden40_public_safe", 40),
    (ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl", "open_structured", 32),
    (ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl", "open_structured_long", 28),
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_lines(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or len(rows) >= limit:
            break
        rows.append(json.loads(line))
    return rows


def build(*, max_total: int = 100, out_path: Path = DEFAULT_OUT) -> dict[str, Any]:
    merged: list[dict[str, Any]] = []
    source_stats: list[dict[str, Any]] = []
    for path, tag, cap in SOURCES:
        if len(merged) >= max_total:
            break
        take = min(cap, max_total - len(merged))
        chunk = _read_lines(path, take)
        for i, obj in enumerate(chunk):
            obj = dict(obj)
            obj["id"] = f"proof-{tag}-{i:03d}"
            obj["proof_sprint_source"] = tag
            obj["public_safe"] = True
            obj["forbidden_as_customer_sla"] = True
            obj["research_only"] = True
            merged.append(obj)
        source_stats.append(
            {
                "tag": tag,
                "path": path.relative_to(ROOT).as_posix() if path.is_file() else None,
                "rows_used": len(chunk),
            }
        )
    out_path = out_path if out_path.is_absolute() else (ROOT / out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "output": out_path.relative_to(ROOT).as_posix(),
        "case_count": len(merged),
        "sources": source_stats,
        "generated_at_utc": _utc(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-total", type=int, default=100)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out = args.out_jsonl.resolve() if args.out_jsonl.is_absolute() else (ROOT / args.out_jsonl).resolve()
    summary = build(max_total=args.max_total, out_path=out)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["case_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
