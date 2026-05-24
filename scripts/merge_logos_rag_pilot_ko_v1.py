#!/usr/bin/env python3
"""Merge philosophy_lane_rag_pilot_r4_q*_ko_latest.json blocks for bridge ingest."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT_R6 = PILOT / "philosophy_lane_rag_pilot_r6_merged_q01_q12_ko_only_latest.json"
DEFAULT_OUT_R4 = PILOT / "philosophy_lane_rag_pilot_r4_merged_q01_q12_ko_latest.json"
DEFAULT_SSOT = ROOT / "docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json"


def _pilot_glob_paths() -> tuple[list[Path], str]:
    r6 = sorted(PILOT.glob("philosophy_lane_rag_pilot_r6_q*_ko_only_latest.json"))
    if r6:
        return r6, "r6_ko_only"
    r4 = sorted(PILOT.glob("philosophy_lane_rag_pilot_r4_q*_ko_latest.json"))
    return r4, "r4_ko"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None, help="Default: r6 merged if r6 pilots exist.")
    ap.add_argument("--copy-to-ssot", type=Path, default=DEFAULT_SSOT)
    ap.add_argument("--max-blocks-per-pilot", type=int, default=5)
    ap.add_argument(
        "--glob",
        type=str,
        default=None,
        help="Override pilot glob; default prefers r6 ko_only then r4 ko.",
    )
    ap.add_argument("--version-tag", type=str, default="1.1.0")
    args = ap.parse_args()

    if args.glob:
        paths = sorted(PILOT.glob(args.glob))
        lane = "custom_glob"
    else:
        paths, lane = _pilot_glob_paths()
    out_path = args.out or (DEFAULT_OUT_R6 if lane == "r6_ko_only" else DEFAULT_OUT_R4)
    if not paths:
        print("No pilot q*_ko files found", flush=True)
        return 2

    blocks: list[dict[str, Any]] = []
    sources: list[str] = []
    for p in paths:
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        src_blocks = doc.get("blocks") if isinstance(doc.get("blocks"), list) else []
        for b in src_blocks[: max(1, args.max_blocks_per_pilot)]:
            if isinstance(b, dict):
                blocks.append(b)
        sources.append(p.name)

    merged: dict[str, Any] = {
        "schema": "philosophy_lane_rag_pilot_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "menu_id": "mkm_philosophy_chat_v1",
        "track": "B",
        "research_only": True,
        "non_gating_ack": True,
        "status": "ok",
        "merge_sources": sources,
        "pilot_lane": lane,
        "blocks": blocks[:24],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.copy_to_ssot:
        args.copy_to_ssot.parent.mkdir(parents=True, exist_ok=True)
        args.copy_to_ssot.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out_path), "pilot_lane": lane, "blocks": len(merged["blocks"]), "sources": len(sources)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
