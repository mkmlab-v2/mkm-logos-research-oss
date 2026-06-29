#!/usr/bin/env python3
"""Post-Tier-3 Oracle Logos passive ops chain ([HYPO] / B-track).

Weekly-style bundle after Tier-2+3 unlock: observability · gates · A2A wire · manifest · resume.

  py scripts/run_logos_oracle_post_tier3_passive_ops_chain_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_oracle_post_tier3_passive_ops_chain_v1_latest.json"
OBS = ROOT / "docs/final/artifacts/logos_oracle_narrative_closure_observability_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []
    commands = [
        ("narrative_closure_observability", [sys.executable, "scripts/run_logos_oracle_narrative_closure_observability_chain_v1.py", "--skip-pytest"]),
        ("tier3_protocol_verify", [sys.executable, "scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py", "--require-tier3-unlock"]),
        ("miswire_guard", [sys.executable, "scripts/check_logos_track_a_miswire_guard_v1.py"]),
        ("a2a_oracle_wire_handoff", [sys.executable, "scripts/build_a2a_tier3_cursor_wire_handoff_pilot_v1.py", "--lane", "oracle"]),
        ("tier2_manifest", [sys.executable, "scripts/build_logos_oracle_tier2_cursor_inject_manifest_v1.py"]),
        ("oracle_resume_pack", [sys.executable, "scripts/build_mkm_chat_resume_pack_v1.py", "--lane", "oracle"]),
    ]
    for name, cmd in commands:
        proc = subprocess.run(cmd, cwd=ROOT, check=False)
        steps.append({"step": name, "exit_code": proc.returncode})
        if proc.returncode != 0:
            print(f"FAIL: {name} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_logos_oracle_narrative_closure_observability_v1.py",
                "-q",
            ],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    obs = json.loads(OBS.read_text(encoding="utf-8-sig")) if OBS.is_file() else {}
    report = {
        "schema": "logos_oracle_post_tier3_passive_ops_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "chain_pass": True,
        "observation_pass": obs.get("observation_pass"),
        "observations": f"{obs.get('observations_pass_count')}/{obs.get('observations_total')}",
        "tier3_unlock": True,
        "passive_green": obs.get("observation_pass") is True,
        "steps": steps,
        "repro_one_shot": "py scripts/run_logos_oracle_post_tier3_passive_ops_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"chain_pass=true passive_green={report['passive_green']} "
        f"obs={report['observations']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
