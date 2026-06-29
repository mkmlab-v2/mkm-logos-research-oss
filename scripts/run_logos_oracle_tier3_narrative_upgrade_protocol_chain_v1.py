#!/usr/bin/env python3
"""Oracle Logos Tier-3 narrative upgrade protocol chain ([HYPO] / B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_OUT = ROOT / "docs/final/artifacts/logos_oracle_tier3_narrative_upgrade_protocol_v1_latest.json"
REPORT = ROOT / "reports/logos_oracle_tier3_narrative_upgrade_protocol_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--require-tier3-unlock", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "tier2_protocol_refresh", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_oracle_tier3_narrative_upgrade_protocol_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "build_tier3_protocol", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_oracle_tier2_cursor_inject_manifest_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "build_tier2_manifest", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_oracle_cursor_inject_tier1_readiness_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "readiness_refresh", "exit_code": proc.returncode})
    if proc.returncode != 0:
        return proc.returncode

    protocol = json.loads(PROTOCOL_OUT.read_text(encoding="utf-8-sig"))
    tier3_unlock = bool(protocol.get("tier3_constitution_narrative_full_upgrade_ready"))
    if args.require_tier3_unlock and not tier3_unlock:
        print("FAIL: tier3 unlock pending commander+legal gates", file=sys.stderr)
        for row in protocol.get("blocker_release_matrix") or []:
            if not row.get("released"):
                print(f"  BLOCKED: {row.get('blocker_id')}", file=sys.stderr)
        return 2

    report = {
        "schema": "logos_oracle_tier3_narrative_upgrade_protocol_chain_v1",
        "generated_at_utc": _utc_now(),
        "chain_pass": True,
        "tier3_constitution_narrative_full_upgrade_ready": tier3_unlock,
        "blockers_released": sum(
            1 for b in protocol.get("blocker_release_matrix") or [] if b.get("released")
        ),
        "protocol_artifact": str(PROTOCOL_OUT.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "repro_one_shot": "py scripts/run_logos_oracle_tier3_narrative_upgrade_protocol_chain_v1.py",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"chain_pass=true tier3_unlock={tier3_unlock} blockers={report['blockers_released']}/4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
