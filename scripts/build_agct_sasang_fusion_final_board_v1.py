#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build final fusion board for AGCT Sasang Stage2 operations.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--status-board-json", type=Path, default=root / "reports" / "agct_sasang_global_status_board_v1_latest.json")
    ap.add_argument("--coordinator-json", type=Path, default=root / "reports" / "mkm_global_coordinator_v1_latest.json")
    ap.add_argument("--promotion-gate-json", type=Path, default=root / "reports" / "agct_sasang_stage2_promotion_gate_v1_latest.json")
    ap.add_argument("--fasttrack-gate-json", type=Path, default=root / "reports" / "agct_sasang_stage2_fasttrack_gate_v1_latest.json")
    ap.add_argument("--d7-json", type=Path, default=root / "reports" / "agct_sasang_stage2_d7_checkpoint_v1_latest.json")
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_sasang_fusion_final_board_v1_latest.json")
    ns = ap.parse_args()

    status_board = _read_json(ns.status_board_json)
    coordinator = _read_json(ns.coordinator_json)
    promotion = _read_json(ns.promotion_gate_json)
    fasttrack = _read_json(ns.fasttrack_gate_json)
    d7 = _read_json(ns.d7_json)

    payload = {
        "schema": "agct_sasang_fusion_final_board_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "final_board": {
            "baseline_status": status_board.get("status_board", {}).get("baseline_status"),
            "global_action": coordinator.get("decision", {}).get("action"),
            "global_agreement_rate": coordinator.get("fusion", {}).get("agreement_rate"),
            "stage2_promotion_decision": promotion.get("decision"),
            "stage2_fasttrack_decision": fasttrack.get("decision"),
            "stage2_d7_status": d7.get("status"),
            "alert_reasons": status_board.get("status_board", {}).get("alert_reasons", []),
        },
        "artifacts": {
            "status_board_json": str(ns.status_board_json.resolve()),
            "coordinator_json": str(ns.coordinator_json.resolve()),
            "promotion_gate_json": str(ns.promotion_gate_json.resolve()),
            "fasttrack_gate_json": str(ns.fasttrack_gate_json.resolve()),
            "d7_json": str(ns.d7_json.resolve()),
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
