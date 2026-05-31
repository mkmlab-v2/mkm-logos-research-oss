#!/usr/bin/env python3
"""Measure token footprint: full ops anchor slices vs resume inject pins.

[HYPO] / research_only — not Track A KPI. Uses tiktoken when installed; else char/4 estimate.

  py scripts/bench_mkm_ops_memory_index_token_savings_v1.py
  py scripts/bench_mkm_ops_memory_index_token_savings_v1.py --out reports/mkm_ops_memory_index_token_bench_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    NODE_SPECS,
    build_node_entry,
    extract_node_from_index,
    load_index,
    top_nodes_by_priority,
    utc_now_iso,
)


def _count_tokens(text: str, *, encoding_name: str = "cl100k_base") -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        count = len(enc.encode(text))
        return {"tokens": count, "method": f"tiktoken:{encoding_name}"}
    except Exception as exc:  # noqa: BLE001 — bench fallback only
        est = max(1, len(text) // 4)
        return {
            "tokens": est,
            "method": "char_div_4_estimate",
            "note": f"tiktoken unavailable ({exc})",
        }


def _full_slice_text(root: Path) -> str:
    parts: list[str] = []
    for spec in NODE_SPECS:
        entry = build_node_entry(root, spec)
        block = extract_node_from_index(root, entry)
        parts.append(block)
    return "\n\n---\n\n".join(parts)


def _inject_text(root: Path, *, top_n: int) -> str:
    index = load_index(DEFAULT_INDEX_PATH)
    lines: list[str] = []
    for node_id, node in top_nodes_by_priority(index, top_n=top_n):
        lines.append(node.get("essence") or "")
        for tag in node.get("must_keep_tags") or []:
            lines.append(tag)
        lines.append(f"[node:{node_id}]")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_ROOT / "reports" / "mkm_ops_memory_index_token_bench_v1_latest.json",
    )
    ap.add_argument("--top-n", type=int, default=2)
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    mission_log = root / "MISSION_LOG.md"
    if not mission_log.is_file():
        print(f"FAIL: MISSION_LOG.md missing at {mission_log}", file=sys.stderr)
        return 1
    if not DEFAULT_INDEX_PATH.is_file():
        print(f"FAIL: index missing — run build_mkm_ops_memory_index_v1.py first", file=sys.stderr)
        return 1

    try:
        full_text = _full_slice_text(root)
        inject_text = _inject_text(root, top_n=args.top_n)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: bench input: {exc}", file=sys.stderr)
        return 1

    full_count = _count_tokens(full_text)
    inject_count = _count_tokens(inject_text)
    full_t = int(full_count["tokens"])
    inject_t = int(inject_count["tokens"])
    saved = max(0, full_t - inject_t)
    ratio = round(saved / full_t, 4) if full_t else 0.0

    doc: dict[str, Any] = {
        "schema": "mkm_ops_memory_index_token_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] token bench — not commercial SLA; measure only",
        "generated_at_utc": utc_now_iso(),
        "top_n_inject_pins": args.top_n,
        "full_anchor_slices": {
            "char_count": len(full_text),
            **full_count,
        },
        "inject_pins_text": {
            "char_count": len(inject_text),
            **inject_count,
        },
        "delta": {
            "tokens_saved_vs_full_slices": saved,
            "reduction_ratio": ratio,
            "reduction_percent": round(ratio * 100, 2),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"full={full_t} inject={inject_t} saved={saved} "
        f"reduction={doc['delta']['reduction_percent']}% ({full_count['method']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
