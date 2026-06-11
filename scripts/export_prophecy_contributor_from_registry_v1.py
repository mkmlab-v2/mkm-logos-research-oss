#!/usr/bin/env python3
"""Export general_prophecy registry questions to contributor JSONL rows [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CONTRIBUTOR_LABELS = ["contributor_provided", "research_only", "prophecy_bench_v1"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_contributor_row(q: dict[str, Any], *, provenance_note: str | None = None) -> dict[str, Any]:
    out = dict(q)
    out["schema"] = "prophecy_contributor_question_v1"
    out["contributor_provided"] = True
    out["customer_provided"] = False
    out["send_gate"] = "HOLD"
    out["ready_for_external_send"] = False
    labels = list(CONTRIBUTOR_LABELS)
    for tag in q.get("domain_tags") or []:
        if tag not in labels:
            labels.append(str(tag))
    out["labels"] = labels
    if provenance_note:
        out["provenance_note"] = provenance_note
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-json", type=Path, required=True)
    ap.add_argument("--out-jsonl", type=Path, required=True)
    ap.add_argument("--provenance-note", default="exported_from_registry_fixture")
    ap.add_argument("--max-rows", type=int, default=None)
    args = ap.parse_args()

    reg = json.loads(args.registry_json.read_text(encoding="utf-8"))
    questions = reg.get("questions") or []
    rows: list[dict[str, Any]] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if args.max_rows is not None and len(rows) >= args.max_rows:
            break
        rows.append(to_contributor_row(q, provenance_note=args.provenance_note))

    out = args.out_jsonl.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "rows": len(rows), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
