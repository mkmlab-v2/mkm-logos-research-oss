#!/usr/bin/env python3
"""Append one insight_observation_log.jsonl row (B-tier contract)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "data" / "myeongni" / "insight_observation_log.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description="Append B-track insight row to insight_observation_log.jsonl")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--inputs-summary", required=True)
    ap.add_argument("--insight-one-liner", required=True)
    ap.add_argument("--falsification-hook", required=True)
    ap.add_argument("--confidence", type=float, default=None)
    ap.add_argument("--note", default="btrack_daily_chain")
    args = ap.parse_args()

    row = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs_summary": args.inputs_summary.strip(),
        "insight_one_liner": args.insight_one_liner.strip(),
        "falsification_hook": args.falsification_hook.strip(),
        "confidence": args.confidence,
        "snapshot_refs": [
            "btrack_llm_input_bundle_latest.json",
            "independent_lens_fusion_stub_latest.json",
            "independent_lens_shadow_minority_monthly_latest.json",
        ],
        "note": args.note.strip(),
    }
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"APPENDED: {args.log.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
