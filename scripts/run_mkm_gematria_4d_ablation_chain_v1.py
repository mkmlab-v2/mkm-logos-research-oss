#!/usr/bin/env python3
"""K-track Gematria 4D ablation chain — NOT router/gold/prophecy Brier ([HYPO]).

  py scripts/run_mkm_gematria_4d_ablation_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_gematria_4d_ablation_chain_v1_latest.json"
ABLATION = ROOT / "docs/final/artifacts/gematria_4d_ablation_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args()

    proc = subprocess.run(
        [sys.executable, "scripts/build_gematria_4d_ablation_v1.py"],
        cwd=ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode

    doc = json.loads(ABLATION.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "gematria_4d_ablation_v1":
        print("FAIL: schema mismatch", file=sys.stderr)
        return 1
    if doc.get("source_track") != "K":
        print("FAIL: source_track must be K", file=sys.stderr)
        return 1
    if not doc.get("research_only"):
        print("FAIL: research_only required", file=sys.stderr)
        return 1

    snap = doc.get("snapshot") or {}
    delta = snap.get("delta_with_minus_without")
    if not isinstance(delta, (int, float)):
        print("FAIL: missing delta_with_minus_without", file=sys.stderr)
        return 1

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_mkm_gematria_4d_ablation_chain_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    report = {
        "schema": "mkm_gematria_4d_ablation_chain_v1",
        "chain_pass": True,
        "research_only": True,
        "source_track": "K",
        "send_gate": "HOLD",
        "boundary_ack": (
            "K-track heuristic on/off score diff only — do not merge with "
            "router_hit, gold_required_all_pass, or prophecy Brier tables."
        ),
        "snapshot": snap,
        "policy_gate": doc.get("policy_gate"),
        "sources": doc.get("sources"),
        "repro_one_shot": "py scripts/run_mkm_gematria_4d_ablation_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"chain_pass=true source_track=K delta={delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
