#!/usr/bin/env python3
"""Lane resume pack vs naive full-paste token bench ([HYPO] / B-track).

Compares MISSION_LOG + CENTRAL full read vs lane-specific ops inject pins.

  py scripts/bench_mkm_ltm_resume_lane_token_v1.py
  py scripts/bench_mkm_ltm_resume_lane_token_v1.py --out reports/mkm_ltm_resume_lane_token_bench_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_ltm_lane_purity_lib_v1 import lane_purity_violations  # noqa: E402
from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    LANE_OPS_PACKS,
    load_index,
    nodes_for_resume,
    utc_now_iso,
)


def _count_tokens(text: str, *, encoding_name: str = "cl100k_base") -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        return {"tokens": len(enc.encode(text)), "method": f"tiktoken:{encoding_name}"}
    except Exception as exc:  # noqa: BLE001
        est = max(1, len(text) // 4)
        return {
            "tokens": est,
            "method": "char_div_4_estimate",
            "note": str(exc),
        }


def _naive_baseline_text(root: Path) -> str:
    parts: list[str] = []
    mission = root / "MISSION_LOG.md"
    central = root / "docs" / "final" / "CENTRAL_AGENT_MEMORY_V1.md"
    if mission.is_file():
        parts.append(mission.read_text(encoding="utf-8", errors="replace"))
    if central.is_file():
        parts.append(central.read_text(encoding="utf-8", errors="replace"))
    return "\n\n---\n\n".join(parts)


def _lane_inject_text(root: Path, lane: str) -> str:
    index = load_index(DEFAULT_INDEX_PATH)
    lines: list[str] = []
    for _node_id, node in nodes_for_resume(index, lane=lane, root=root):
        lines.append(node.get("essence") or "")
        for tag in node.get("must_keep_tags") or []:
            lines.append(str(tag))
    return "\n".join(lines)


def _lane_must_keep_overlay_terms(root: Path, lane: str) -> list[str]:
    index = load_index(DEFAULT_INDEX_PATH)
    seen: set[str] = set()
    tags: list[str] = []
    for _node_id, node in nodes_for_resume(index, lane=lane, root=root):
        for tag in node.get("must_keep_tags") or []:
            t = str(tag).strip()
            if t and t not in seen:
                seen.add(t)
                tags.append(t)
    return tags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument(
        "--out",
        type=Path,
        default=SCRIPT_ROOT
        / "reports"
        / "mkm_ltm_resume_lane_token_bench_v1_latest.json",
    )
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    if not DEFAULT_INDEX_PATH.is_file():
        print("FAIL: ops index missing — run build_mkm_ops_memory_index_v1.py", file=sys.stderr)
        return 1

    baseline = _naive_baseline_text(root)
    if not baseline.strip():
        print("FAIL: naive baseline empty (MISSION_LOG + CENTRAL)", file=sys.stderr)
        return 1

    baseline_count = _count_tokens(baseline)
    baseline_t = int(baseline_count["tokens"])

    lanes: dict[str, Any] = {}
    purity_errors: list[str] = []
    for lane in sorted(LANE_OPS_PACKS):
        try:
            inject = _lane_inject_text(root, lane)
        except (KeyError, ValueError, FileNotFoundError) as exc:
            print(f"FAIL: lane {lane}: {exc}", file=sys.stderr)
            return 1
        inject_count = _count_tokens(inject)
        inject_t = int(inject_count["tokens"])
        saved = max(0, baseline_t - inject_t)
        ratio = round(saved / baseline_t, 4) if baseline_t else 0.0
        flags = lane_purity_violations(lane, inject)
        if flags:
            purity_errors.extend([f"{lane}:{f}" for f in flags])
        lanes[lane] = {
            "node_ids": list(LANE_OPS_PACKS[lane]),
            "char_count": len(inject),
            "inject_pins": {**inject_count},
            "saved_tokens_vs_naive_baseline": saved,
            "savings_ratio_vs_naive_baseline": ratio,
            "purity_flags": flags,
        }

    doc: dict[str, Any] = {
        "schema": "mkm_ltm_resume_lane_token_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] lane token bench — not commercial SLA",
        "generated_at_utc": utc_now_iso(),
        "naive_baseline": {
            "sources": ["MISSION_LOG.md", "docs/final/CENTRAL_AGENT_MEMORY_V1.md"],
            "char_count": len(baseline),
            **baseline_count,
        },
        "lanes": lanes,
        "aggregate": {
            "lane_count": len(lanes),
            "mean_savings_ratio": round(
                sum(l["savings_ratio_vs_naive_baseline"] for l in lanes.values())
                / max(1, len(lanes)),
                4,
            ),
        },
        "purity_errors": purity_errors,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(
        f"naive_baseline_tokens={baseline_t} "
        f"mean_lane_savings_ratio={doc['aggregate']['mean_savings_ratio']}"
    )
    for lane, row in lanes.items():
        print(
            f"  {lane}: inject_tokens={row['inject_pins']['tokens']} "
            f"savings_ratio={row['savings_ratio_vs_naive_baseline']}"
        )
    if purity_errors:
        for err in purity_errors:
            print(f"WARN purity: {err}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
