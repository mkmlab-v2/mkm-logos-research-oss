#!/usr/bin/env python3
"""Convert masked customer JSONL rows into spine bench input (compression_cases)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "compression_customer_jsonl_spine_bench_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in ("text", "raw_text", "content", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None


def build_from_jsonl(jsonl_path: Path, *, max_cases: int = 50) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for i, line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or len(cases) >= max_cases:
            break
        obj = json.loads(line)
        text = _row_text(obj)
        if not text:
            continue
        cases.append(
            {
                "id": str(obj.get("id") or f"customer-case-{i:03d}"),
                "raw_text": text,
                "domain_tag": obj.get("domain_tag"),
                "labels": list(obj.get("labels") or []),
                "customer_provided": bool(obj.get("customer_provided")),
            }
        )
    if len(cases) < 20:
        raise ValueError(f"need >=20 cases, got {len(cases)} from {jsonl_path}")
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "source_jsonl": str(jsonl_path.relative_to(ROOT)).replace("\\", "/"),
        "compression_cases": cases,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--max-cases", type=int, default=50)
    args = ap.parse_args()

    jsonl = args.jsonl if args.jsonl.is_absolute() else ROOT / args.jsonl
    if not jsonl.is_file():
        print(f"missing jsonl: {jsonl}", file=sys.stderr)
        return 2

    doc = build_from_jsonl(jsonl, max_cases=args.max_cases)
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "cases": len(doc["compression_cases"]), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
