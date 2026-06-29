#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit market_sasang_lens from market_psych v2 map (machine_readables bridge)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_psych_v2_lens_bridge_v1 import (  # noqa: E402
    load_latest_v2_mapping,
    sasang_upstream_stub_from_v2_mapping,
)
from scripts.market_sasang_lens_engine_v1 import build_market_sasang_lens_payload, load_policy  # noqa: E402

DEFAULT_POLICY = ROOT / "data/market_sasang/market_sasang_lens_policy_v1.json"
DEFAULT_MAP = ROOT / "reports/market_psych_sasang_axis_map_v2_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/market_sasang_lens_from_market_psych_v2_latest.json"
COMPARE_OUT = ROOT / "reports/market_sasang_lens_upstream_vs_v2_bridge_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--map-json", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--compare-upstream",
        type=Path,
        default=ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json",
        help="Optional: compare softmax vs legacy upstream.",
    )
    ap.add_argument("--write-compare", action="store_true", default=True)
    args = ap.parse_args()

    if not args.map_json.is_file():
        print(f"missing {args.map_json}", file=sys.stderr)
        return 2

    policy = load_policy(args.policy)
    map_doc = json.loads(args.map_json.read_text(encoding="utf-8"))
    eval_date, mapping = load_latest_v2_mapping(map_doc)
    upstream_v2 = sasang_upstream_stub_from_v2_mapping(mapping, eval_date=eval_date)

    payload = build_market_sasang_lens_payload(
        sasang_lens_doc=upstream_v2,
        policy=policy,
        policy_path=str(args.policy.resolve()),
        source_input_path=str(args.map_json.resolve()),
    )
    payload["ts_utc"] = _utc_now()
    payload["input_bridge"] = {
        "schema": "market_psych_v2_lens_bridge_v1",
        "manifest": "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json",
        "eval_date": eval_date,
        "machine_readables_source": "market_psych_v2",
    }
    payload["byungjeung_v2"] = mapping.get("byungjeung")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")

    if args.write_compare and args.compare_upstream.is_file():
        legacy = json.loads(args.compare_upstream.read_text(encoding="utf-8"))
        legacy_payload = build_market_sasang_lens_payload(
            sasang_lens_doc=legacy,
            policy=policy,
            policy_path=str(args.policy.resolve()),
            source_input_path=str(args.compare_upstream.resolve()),
        )
        compare = {
            "schema": "market_sasang_lens_upstream_vs_v2_bridge_v1",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "eval_date_v2": eval_date,
            "legacy_upstream_path": str(args.compare_upstream.resolve()),
            "v2_map_path": str(args.map_json.resolve()),
            "state_vector_legacy": legacy_payload.get("state_vector_sasang_softmax"),
            "state_vector_v2_bridge": payload.get("state_vector_sasang_softmax"),
            "veto_legacy": legacy_payload.get("veto"),
            "veto_v2_bridge": payload.get("veto"),
            "fusion_bridge_legacy": legacy_payload.get("fusion_bridge"),
            "fusion_bridge_v2": payload.get("fusion_bridge"),
            "note_ko": "Softmax diff shows vocabulary alignment gap between dynamics-jsonl upstream vs v2 psych bridge.",
        }
        COMPARE_OUT.parent.mkdir(parents=True, exist_ok=True)
        COMPARE_OUT.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        art = ROOT / "docs/final/artifacts/market_sasang_lens_upstream_vs_v2_bridge_v1_latest.json"
        art.write_text(json.dumps(compare, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {COMPARE_OUT.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
