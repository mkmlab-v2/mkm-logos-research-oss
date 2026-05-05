#!/usr/bin/env python3
"""Validate fixed 12-state proxy mapping artifact contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_proxy_mapping_v1_latest.json"
EXPECTED_CONSTITUTIONS = {"taeyang", "soyanga", "taeeum", "soeum"}
EXPECTED_STAGES = {"onset", "peak", "exhaustion"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mapping-json", type=Path, default=DEFAULT_PATH)
    args = ap.parse_args()

    if not args.mapping_json.is_file():
        print(f"missing mapping: {args.mapping_json}")
        return 2

    payload = json.loads(args.mapping_json.read_text(encoding="utf-8"))
    if payload.get("schema") != "sasang_12state_proxy_mapping_v1":
        print("invalid schema")
        return 3

    states = payload.get("states")
    if not isinstance(states, list) or len(states) != 12:
        print("invalid state count")
        return 4

    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for s in states:
        if not isinstance(s, dict):
            print("invalid state item type")
            return 5
        sid = str(s.get("state_id", ""))
        constitution = str(s.get("constitution", ""))
        stage = str(s.get("stage", ""))
        proxy_rules = s.get("proxy_rules")
        if not sid or sid in seen_ids:
            print("state id missing/duplicated")
            return 6
        if constitution not in EXPECTED_CONSTITUTIONS:
            print("invalid constitution")
            return 7
        if stage not in EXPECTED_STAGES:
            print("invalid stage")
            return 8
        if not isinstance(proxy_rules, dict) or not proxy_rules:
            print("missing proxy rules")
            return 9
        pair = (constitution, stage)
        if pair in seen_pairs:
            print("duplicate constitution-stage pair")
            return 10
        seen_ids.add(sid)
        seen_pairs.add(pair)

    fixed_params = payload.get("fixed_params")
    if not isinstance(fixed_params, dict) or "adx_period" not in fixed_params or "rsi_period" not in fixed_params:
        print("missing fixed params")
        return 11

    contract = payload.get("validation_contract")
    if not isinstance(contract, dict) or "walkforward" not in contract or "promotion_gate" not in contract:
        print("missing validation contract")
        return 12

    print("ok sasang_12state_proxy_mapping_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
