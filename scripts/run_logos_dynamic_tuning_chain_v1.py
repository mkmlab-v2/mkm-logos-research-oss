#!/usr/bin/env python3
"""Logos dynamic tuning composite chain — sandbox + force W + geumhwa → dynamic stats."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_dynamic_resonance_stats_v1_latest.json"
POINTER = ROOT / "docs/final/artifacts/logos_theory_to_code_pointer_v1_latest.json"


def _write_theory_pointer() -> None:
    doc = {
        "schema": "logos_theory_to_code_pointer_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_class": "HYPO",
        "pointers": [
            {
                "theory": "MKM_WORLDVIEW_75 / 금화교역",
                "doc": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
                "code": "docs/verified_knowledge_base/unified_field_theory/geumhwa_exchange.json",
            },
            {
                "theory": "4D spread sandbox (B-track)",
                "doc": "scripts/core/gematria_to_4d_bridge_sandbox_v1.py",
                "code": "scripts/build_logos_cosmic_anchor_batch_sandbox_v1.py",
            },
            {
                "theory": "HG-5 fundamental force lexicon",
                "doc": "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json",
                "code": "scripts/core/logos_fundamental_force_lexicon_v1.py",
            },
            {
                "theory": "Dynamic tuning composite",
                "doc": "scripts/core/logos_dynamic_tuning_v1.py",
                "code": "scripts/run_logos_dynamic_tuning_chain_v1.py",
            },
            {
                "theory": "UI lattice / OrbGraphBloom",
                "doc": "projects/mkm/mkm-life/lib/magic-orb-cosmic-anchor-graph-bridge-v1.ts",
                "code": "projects/mkm/mkm-life/public/data/logos_dynamic_resonance_sidecar_v1.json",
            },
        ],
        "forbidden": [
            "gematria_bridge_v1 production overwrite",
            "sidecar to production batch merge",
            "Track A / SEND / live",
        ],
    }
    POINTER.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-spread-chain", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--session-age", type=float, default=1.0)
    args = parser.parse_args()

    steps: list[list[str]] = []
    if not args.skip_spread_chain:
        steps.append([sys.executable, "scripts/run_logos_spread_tuning_chain_v1.py"])
    steps.extend(
        [
            [
                sys.executable,
                "scripts/build_logos_dynamic_resonance_stats_v1.py",
                "--session-age",
                str(args.session_age),
            ],
        ]
    )

    for cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        if proc.returncode != 0:
            print(f"FAIL: {' '.join(cmd[1:])} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {cmd[1]}")

    _write_theory_pointer()
    print(f"OK: theory pointer {POINTER}")

    if not OUT.is_file():
        return 1
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    if not doc.get("summary", {}).get("dynamic_spread_target_met"):
        print("WARN: mean_spread_4d_dynamic < 0.05", file=sys.stderr)

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_dynamic_tuning_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode
        print("OK: pytest dynamic tuning")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
