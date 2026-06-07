#!/usr/bin/env python3
"""Joint frontline gate: fusion PASS + authority READY (metadata only · [HYPO])."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _frontline_legacy_common import ROOT, load_json, research_meta, utc_now, write_json


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fusion-json", type=Path, default=None)
    ap.add_argument("--authority-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    fusion_path = args.fusion_json or ROOT / "outputs" / f"fusion_join_quality_{args.tag}.json"
    authority_path = args.authority_json or ROOT / "outputs" / f"authority_readiness_{args.tag}.json"
    out_path = args.out_json or ROOT / "outputs" / f"joint_frontline_gate_{args.tag}.json"

    fusion = load_json(fusion_path)
    authority = load_json(authority_path)
    fusion_ok = str(fusion.get("status") or "").upper() == "PASS"
    authority_ok = str(authority.get("status") or "").upper() == "READY"
    status = "PASS" if fusion_ok and authority_ok else "FAIL"

    payload = {
        "schema": "joint_frontline_gate_v1",
        "generated_at_utc": utc_now(),
        "tag": args.tag,
        "status": status,
        "checks": {"fusion_pass": fusion_ok, "authority_ready": authority_ok},
        "inputs": {"fusion_json": str(fusion_path), "authority_json": str(authority_path)},
        **research_meta(),
    }
    write_json(out_path, payload)
    print(f"status={status}\njson={out_path}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
