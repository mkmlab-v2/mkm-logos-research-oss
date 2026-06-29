#!/usr/bin/env python3
"""Oracle Logos Tier-2 incremental append protocol chain ([HYPO] / B-track).

One-shot: sidecar rebuild → protocol → readiness refresh → validate gates.

  py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_OUT = ROOT / "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"
READINESS_OUT = ROOT / "docs/final/artifacts/logos_oracle_cursor_inject_tier1_readiness_v1_latest.json"
REPORT = ROOT / "reports/logos_oracle_tier2_incremental_append_protocol_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-sidecar-rebuild", action="store_true")
    ap.add_argument("--skip-readiness-refresh", action="store_true")
    ap.add_argument("--require-tier2-unlock", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_sidecar_rebuild:
        proc = subprocess.run(
            [sys.executable, "scripts/build_mkm_sidecar_constitution_paths_v1.py"],
            cwd=ROOT,
            check=False,
        )
        steps.append({"step": "sidecar_rebuild", "exit_code": proc.returncode})
        if proc.returncode != 0:
            return proc.returncode

    proc = subprocess.run(
        [sys.executable, "scripts/build_logos_oracle_tier2_incremental_append_protocol_v1.py"],
        cwd=ROOT,
        check=False,
    )
    steps.append({"step": "build_protocol", "exit_code": proc.returncode})
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

    if not args.skip_readiness_refresh:
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/run_logos_oracle_cursor_inject_tier1_readiness_chain_v1.py",
                "--skip-overlay-refresh",
                "--skip-pytest",
            ],
            cwd=ROOT,
            check=False,
        )
        steps.append({"step": "tier1_readiness_refresh", "exit_code": proc.returncode})
        if proc.returncode != 0:
            return proc.returncode

    protocol = json.loads(PROTOCOL_OUT.read_text(encoding="utf-8-sig"))
    readiness = json.loads(READINESS_OUT.read_text(encoding="utf-8-sig")) if READINESS_OUT.is_file() else {}

    tier2_unlock = bool(protocol.get("tier2_cursor_rules_full_upgrade_ready"))
    if args.require_tier2_unlock and not tier2_unlock:
        print("FAIL: tier2_cursor_rules_full_upgrade_ready=false (commander gates pending)", file=sys.stderr)
        for row in protocol.get("blocker_release_matrix") or []:
            if not row.get("released"):
                print(f"  BLOCKED: {row.get('blocker_id')} — {row.get('label')}", file=sys.stderr)
        return 2

    report = {
        "schema": "logos_oracle_tier2_incremental_append_protocol_chain_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "chain_pass": True,
        "tier2_cursor_rules_full_upgrade_ready": tier2_unlock,
        "tier2_prep_ready": readiness.get("tier2_prep_ready"),
        "send_gate": protocol.get("send_gate"),
        "blockers_released": sum(
            1 for b in protocol.get("blocker_release_matrix") or [] if b.get("released")
        ),
        "protocol_artifact": str(PROTOCOL_OUT.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "repro_one_shot": "py scripts/run_logos_oracle_tier2_incremental_append_protocol_chain_v1.py",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"chain_pass=true tier2_unlock={tier2_unlock} "
        f"blockers={report['blockers_released']}/4 send_gate={report['send_gate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
