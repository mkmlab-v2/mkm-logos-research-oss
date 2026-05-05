#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CANDIDATE = ART / "sasang_veto_only_operational_params_v1_latest.json"
DEFAULT_ACTIVE = ART / "sasang_veto_only_active_config_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate veto-only operational parameter artifacts.")
    ap.add_argument("--candidate-json", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--active-json", type=Path, default=DEFAULT_ACTIVE)
    args = ap.parse_args()
    if not args.candidate_json.is_file() or not args.active_json.is_file():
        print("missing candidate/active artifact")
        return 2
    c = json.loads(args.candidate_json.read_text(encoding="utf-8"))
    a = json.loads(args.active_json.read_text(encoding="utf-8"))
    if c.get("schema") != "sasang_veto_only_operational_params_v1":
        print("invalid candidate schema")
        return 3
    if a.get("schema") != "sasang_veto_only_active_config_v1":
        print("invalid active schema")
        return 4
    sel = c.get("selected_candidate")
    if not isinstance(sel, dict) or "veto_set" not in sel or "params" not in sel:
        print("invalid selected candidate block")
        return 5
    if "enabled" not in a:
        print("invalid active config block (enabled)")
        return 6
    branches_c = c.get("asset_branches")
    branches_a = a.get("asset_branches")
    if branches_c is not None or branches_a is not None:
        if not isinstance(branches_c, dict) or "default" not in branches_c:
            print("invalid candidate asset_branches (need default)")
            return 7
        if not isinstance(branches_a, dict) or "default" not in branches_a:
            print("invalid active asset_branches (need default)")
            return 8
        for label, br in (("candidate.default", branches_c.get("default")), ("active.default", branches_a.get("default"))):
            if not isinstance(br, dict) or "veto_set" not in br or "soft_exposure" not in br or "params" not in br:
                print(f"invalid {label} branch slice")
                return 9
        if "BTCUSDT" in branches_c:
            btc_a = branches_a.get("BTCUSDT")
            btc_c = branches_c.get("BTCUSDT")
            if not isinstance(btc_c, dict) or not isinstance(btc_a, dict):
                print("invalid BTCUSDT branch pair")
                return 10
            for key in ("veto_set", "soft_exposure", "params"):
                if key not in btc_a or key not in btc_c:
                    print("invalid BTCUSDT branch slice fields")
                    return 11
    elif "soft_exposure" not in a:
        print("invalid active config block (soft_exposure legacy)")
        return 6
    print("ok sasang_veto_only_operational_params_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
