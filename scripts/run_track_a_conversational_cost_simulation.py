#!/usr/bin/env python3
"""Track A conversational cost simulation (bench-linked, not billing).

Reads KPI gate + MULTILENS active report; writes
``docs/final/artifacts/track_a_conversational_cost_simulation_latest.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_saving_rate(active: dict) -> float:
    cm = active.get("compression_metrics") or {}
    v = cm.get("global_token_saving_rate")
    if isinstance(v, (int, float)):
        return float(v)
    raise ValueError("MULTILENS active report missing compression_metrics.global_token_saving_rate")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--kpi-gate",
        type=Path,
        default=None,
        help="Path to general_compression_kpi_gate_v2.json (default: under workspace-root)",
    )
    ap.add_argument(
        "--active-report",
        type=Path,
        default=None,
        help="Path to MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON (default: docs/final/artifacts/track_a_conversational_cost_simulation_latest.json)",
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    kpi = (args.kpi_gate or root / "docs/final/artifacts/general_compression_kpi_gate_v2.json").resolve()
    active = (args.active_report or root / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json").resolve()
    out = (args.out or root / "docs/final/artifacts/track_a_conversational_cost_simulation_latest.json").resolve()

    if not kpi.is_file():
        print(f"error: missing kpi gate: {kpi}", file=sys.stderr)
        return 2
    if not active.is_file():
        print(f"error: missing active report: {active}", file=sys.stderr)
        return 2

    gate_doc = _load_json(kpi)
    decision = str(gate_doc.get("decision") or "").upper()
    gate_decision = "GO" if decision == "GO" else "HOLD"

    active_doc = _load_json(active)
    saving = _extract_saving_rate(active_doc)
    baseline = 1_000_000.0
    after = int(round(baseline * (1.0 - saving)))

    ts = _utc()
    payload = {
        "schema": "track_a_conversational_cost_simulation_v1",
        "generated_at_utc": ts,
        "ts_utc": ts,
        "gate_decision": gate_decision,
        "global_token_saving_rate": saving,
        "hypothesis_monthly_baseline_tokens": baseline,
        "hypothesis_monthly_after_tokens": after,
        "sources": {
            "active_report": str(active).replace("\\", "/"),
            "kpi_gate": str(kpi).replace("\\", "/"),
        },
        "note": "Not billing or live routing; bench-linked scenario only.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
