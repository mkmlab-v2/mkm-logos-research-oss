#!/usr/bin/env python3
"""Non-destructive rollback drill evidence for prophecy live controls."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OPS = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops"

DEFAULT_POLICY = ART / "prophecy_live_rollback_policy_v1_latest.json"
DEFAULT_HEALTH = OPS / "live_trading_health_latest.json"
DEFAULT_BLOCKERS = OPS / "live_trading_blockers_latest.json"
DEFAULT_OUT = ART / "prophecy_live_rollback_drill_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    policy = _load(DEFAULT_POLICY)
    health = _load(DEFAULT_HEALTH)
    blockers = _load(DEFAULT_BLOCKERS)

    health_pass = str(health.get("result") or "") == "PASS"
    blockers_pass = str(blockers.get("result") or "") == "PASS"
    drill_pass = health_pass and blockers_pass and bool(policy)

    out = {
        "schema": "prophecy_live_rollback_drill_v1",
        "generated_at_utc": _now(),
        "mode": "non_destructive_simulation",
        "inputs": {
            "rollback_policy": str(DEFAULT_POLICY).replace("\\", "/"),
            "live_health": str(DEFAULT_HEALTH).replace("\\", "/"),
            "live_blockers": str(DEFAULT_BLOCKERS).replace("\\", "/"),
        },
        "checks": {
            "rollback_policy_present": bool(policy),
            "health_pass": health_pass,
            "blockers_pass": blockers_pass,
        },
        "drill_result": "PASS" if drill_pass else "FAIL",
        "runbook": {
            "trigger": "loss/gate/data gap threshold breach",
            "step_1": "disable live trigger immediately",
            "step_2": "revert to previous candidate-only mode",
            "step_3": "run health+blocker checks and capture evidence",
            "step_4": "require human re-approval before re-enable",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"drill_result={out['drill_result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
