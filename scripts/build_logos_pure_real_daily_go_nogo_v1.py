#!/usr/bin/env python3
"""Build single-file daily GO/NO_GO decision for pure-real operations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_GATE_STATUS = ART / "logos_pure_real_execution_gate_status_latest.json"
DEFAULT_PREFLIGHT = ART / "logos_pure_real_intake_preflight_status_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_daily_go_nogo_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real daily GO/NO_GO decision.")
    ap.add_argument("--gate-status-json", type=Path, default=DEFAULT_GATE_STATUS)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate = _load_json(args.gate_status_json)
    preflight = _load_json(args.preflight_json)

    gate_status = str(gate.get("gate_status") or "")
    blockers = list(gate.get("blockers") or [])
    preflight_status = str(preflight.get("status") or "")
    shortage_rows = int(preflight.get("shortage_rows_today") or 0)

    go = gate_status == "PASS_EXECUTION_AND_DELTA_OK" and preflight_status == "PASS_INTAKE_READY"
    decision = "GO" if go else "NO_GO"

    reasons: list[str] = []
    if gate_status != "PASS_EXECUTION_AND_DELTA_OK":
        reasons.append(f"GATE_STATUS={gate_status or 'MISSING'}")
    if preflight_status != "PASS_INTAKE_READY":
        reasons.append(f"PREFLIGHT_STATUS={preflight_status or 'MISSING'}")
    if shortage_rows > 0:
        reasons.append(f"SHORTAGE_ROWS_TODAY={shortage_rows}")
    for b in blockers:
        reasons.append(f"BLOCKER={b}")

    out = {
        "schema": "logos_pure_real_daily_go_nogo_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "decision": decision,
        "gate_status": gate_status,
        "preflight_status": preflight_status,
        "shortage_rows_today": shortage_rows,
        "reasons": reasons,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output_json": str(args.output_json), "decision": decision, "reason_count": len(reasons)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

