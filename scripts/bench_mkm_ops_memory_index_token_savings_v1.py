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
    assemble_ops_memory_repair_v2_text,
    extract_node_from_index,
    load_index,
    top_nodes_by_priority,
    truncate_anchor_slice,
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


def _full_top_n_slice_text(root: Path, *, top_n: int) -> str:
    """Full anchor paste for the same top-N nodes used by inject pins (apples-to-apples)."""
    index = load_index(DEFAULT_INDEX_PATH)
    parts: list[str] = []
    for _node_id, node in top_nodes_by_priority(index, top_n=top_n):
        block = extract_node_from_index(root, node)
        parts.append(block)
    return "\n\n---\n\n".join(parts)


def _inject_pins_text(
    root: Path,
    *,
    top_n: int,
    include_slice: bool = False,
    slice_max_chars: int = 1200,
) -> str:
    """Mirror build_mkm_chat_resume_pack_v1 ops inject payload."""
    index = load_index(DEFAULT_INDEX_PATH)
    lines: list[str] = []
    for _node_id, node in top_nodes_by_priority(index, top_n=top_n):
        lines.append(node.get("essence") or "")
        for tag in node.get("must_keep_tags") or []:
            lines.append(tag)
        if include_slice:
            block = extract_node_from_index(root, node)
            preview, _truncated = truncate_anchor_slice(
                block, max_chars=slice_max_chars
            )
            lines.append(preview)
    return "\n".join(lines)


def _inject_repair_v2_text(
    root: Path,
    *,
    top_n: int,
    slice_max_chars: int,
) -> tuple[str, str]:
    """Top-priority nodes + synthetic query from essence/tags; repair_v2 noise guard on."""
    index = load_index(DEFAULT_INDEX_PATH)
    routed = list(top_nodes_by_priority(index, top_n=top_n))
    query_parts: list[str] = []
    for _node_id, node in routed:
        essence = node.get("essence")
        if essence:
            query_parts.append(str(essence))
        for tag in node.get("must_keep_tags") or []:
            query_parts.append(str(tag))
    query = " ".join(query_parts)
    if not routed:
        return "", query
    text = assemble_ops_memory_repair_v2_text(
        root,
        routed,
        slice_max_chars=slice_max_chars,
        query=query,
    )
    return text, query


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_ROOT / "reports" / "mkm_ops_memory_index_token_bench_v1_latest.json",
    )
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument(
        "--slice-max-chars",
        type=int,
        default=1200,
        help="Per-node slice cap for resume-pack ON arm (default 1200).",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    mission_log = root / "MISSION_LOG.md"
    if not mission_log.is_file():
        print(f"FAIL: MISSION_LOG.md missing at {mission_log}", file=sys.stderr)
        return 1
    if not DEFAULT_INDEX_PATH.is_file():
        print(f"FAIL: index missing — run build_mkm_ops_memory_index_v1.py first", file=sys.stderr)
        return 1

    full_slice_error: str | None = None
    try:
        inject_off_text = _inject_pins_text(root, top_n=args.top_n, include_slice=False)
        inject_on_text = _inject_pins_text(
            root,
            top_n=args.top_n,
            include_slice=True,
            slice_max_chars=args.slice_max_chars,
        )
        inject_repair_v2_text, repair_query = _inject_repair_v2_text(
            root,
            top_n=args.top_n,
            slice_max_chars=args.slice_max_chars,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: bench input: {exc}", file=sys.stderr)
        return 1

    try:
        full_text = _full_top_n_slice_text(root, top_n=args.top_n)
    except (FileNotFoundError, ValueError) as exc:
        full_text = ""
        full_slice_error = str(exc)

    full_count = _count_tokens(full_text) if full_text else {"tokens": 0, "method": "skipped"}
    inject_off_count = _count_tokens(inject_off_text)
    inject_on_count = _count_tokens(inject_on_text)
    inject_repair_v2_count = _count_tokens(inject_repair_v2_text)
    full_t = int(full_count["tokens"])
    inject_off_t = int(inject_off_count["tokens"])
    inject_on_t = int(inject_on_count["tokens"])
    inject_repair_v2_t = int(inject_repair_v2_count["tokens"])
    saved_vs_full = max(0, full_t - inject_off_t)
    ratio_vs_full = round(saved_vs_full / full_t, 4) if full_t else 0.0
    slice_delta_t = max(0, inject_on_t - inject_off_t)
    slice_ratio = round(slice_delta_t / inject_off_t, 4) if inject_off_t else 0.0

    doc: dict[str, Any] = {
        "schema": "mkm_ops_memory_index_token_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] token bench — not commercial SLA; measure only",
        "generated_at_utc": utc_now_iso(),
        "node_count": len(NODE_SPECS),
        "top_n_inject_pins": args.top_n,
        "slice_max_chars": args.slice_max_chars,
        "comparison_scope": "top_n_inject_pins_full_anchor_vs_inject_off",
        "full_anchor_slices": {
            "char_count": len(full_text),
            **full_count,
            **({"skipped_reason": full_slice_error} if full_slice_error else {}),
        },
        "resume_pack_inject_off": {
            "label": "essence+must_keep_tags only (no --include-slice)",
            "char_count": len(inject_off_text),
            **inject_off_count,
        },
        "resume_pack_inject_on": {
            "label": f"essence+tags+slice preview (--include-slice --slice-max-chars {args.slice_max_chars})",
            "char_count": len(inject_on_text),
            **inject_on_count,
        },
        "resume_pack_inject_repair_v2": {
            "label": (
                f"repair_v2 noise guard (top_n={args.top_n}, slice_max_chars={args.slice_max_chars})"
            ),
            "synthetic_query": repair_query,
            "char_count": len(inject_repair_v2_text),
            **inject_repair_v2_count,
            "operational_label": "post-processor included",
        },
        "delta_vs_full_slices": {
            "tokens_saved_pins_off": saved_vs_full,
            "reduction_ratio": ratio_vs_full,
            "reduction_percent": round(ratio_vs_full * 100, 2),
        },
        "slice_on_off_ab": {
            "tokens_added_by_slice": slice_delta_t,
            "inject_off_tokens": inject_off_t,
            "inject_on_tokens": inject_on_t,
            "overhead_ratio_vs_off": slice_ratio,
            "overhead_percent_vs_off": round(slice_ratio * 100, 2),
        },
        "raw": {
            "label": "resume_pack_inject_on (raw slice, no repair guard)",
            "tokens": inject_on_t,
        },
        "repair_v2": {
            "label": "resume_pack_inject_repair_v2",
            "tokens": inject_repair_v2_t,
            "operational_label": "post-processor included",
        },
        "delta": {
            "tokens_repair_v2_minus_raw": inject_repair_v2_t - inject_on_t,
            "tokens_saved_by_repair_guard": max(0, inject_on_t - inject_repair_v2_t),
        },
        "legacy_alias": {
            "inject_pins_text": "resume_pack_inject_off",
            "delta": "delta_vs_full_slices",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    repair_saved = doc["delta"]["tokens_saved_by_repair_guard"]
    print(
        f"full_slices={full_t} inject_off={inject_off_t} inject_on={inject_on_t} "
        f"repair_v2={inject_repair_v2_t} repair_guard_saved={repair_saved}tok "
        f"saved_vs_full={doc['delta_vs_full_slices']['reduction_percent']}% "
        f"slice_overhead=+{slice_delta_t}tok ({doc['slice_on_off_ab']['overhead_percent_vs_off']}%) "
        f"({full_count['method']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
