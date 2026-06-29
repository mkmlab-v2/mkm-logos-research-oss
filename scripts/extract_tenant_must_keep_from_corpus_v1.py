#!/usr/bin/env python3
"""Extract tenant must_keep overlay candidates from masked customer JSONL (Day 8~14)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-/]{2,}")
IDENT_RE = re.compile(r"(?:[A-Z]{2,}[-_][A-Z0-9]+|ord_[a-z0-9]+|SKU[-_][A-Za-z0-9]+|zone_[a-z])", re.I)

STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "true",
        "false",
        "null",
        "info",
        "level",
        "json",
        "http",
        "post",
        "get",
        "api",
        "v1",
        "v2",
        "v3",
        "seq",
        "bench",
        "text",
        "service",
        "version",
        "status",
        "request",
        "response",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in ("text", "raw_text", "content", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _extract_terms(corpus: Path, *, min_freq: int, max_terms: int) -> tuple[list[str], list[str], dict[str, Any]]:
    counter: Counter[str] = Counter()
    rows = 0
    for line in corpus.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        text = _row_text(obj)
        if not text:
            continue
        rows += 1
        for tok in TOKEN_RE.findall(text):
            low = tok.lower()
            if low in STOP or len(low) < 3:
                continue
            counter[tok] += 1

    hard: list[str] = []
    soft: list[str] = []
    for tok, freq in counter.most_common():
        if freq < min_freq:
            break
        if len(hard) + len(soft) >= max_terms:
            break
        if IDENT_RE.search(tok) or "_" in tok or tok.isupper():
            hard.append(tok)
        else:
            soft.append(tok)

    stats = {
        "rows_scanned": rows,
        "unique_tokens": len(counter),
        "min_freq": min_freq,
        "max_terms": max_terms,
    }
    return hard, soft, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--input-jsonl", type=Path, required=True)
    ap.add_argument("--min-freq", type=int, default=2)
    ap.add_argument("--max-terms", type=int, default=40)
    ap.add_argument(
        "--out-json",
        type=Path,
        help="default: docs/final/artifacts/tenant_<id>_must_keep_overlay_v1.json",
    )
    args = ap.parse_args()

    inp = args.input_jsonl.resolve()
    if not inp.is_file():
        print(f"error: missing corpus: {inp}", file=sys.stderr)
        return 2

    hard, soft, stats = _extract_terms(inp, min_freq=args.min_freq, max_terms=args.max_terms)
    out = args.out_json or (
        ROOT / f"docs/final/artifacts/tenant_{args.tenant_id}_must_keep_overlay_v1.json"
    )
    doc = {
        "schema": "compression_tenant_must_keep_overlay_v1",
        "tenant_id": args.tenant_id,
        "generated_at_utc": _utc(),
        "source_corpus": inp.relative_to(ROOT).as_posix() if inp.is_relative_to(ROOT) else str(inp),
        "labels": ["DRAFT", "research_only", "tenant_policy_overlay_not_full_codebook"],
        "must_keep_hard_terms": hard,
        "must_keep_soft_terms": soft,
        "extraction_stats": stats,
        "boundary_ack": "Overlay join only — not per-tenant 41k offline rebuild.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hard": len(hard), "soft": len(soft), "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
