#!/usr/bin/env python3
"""FinOps wire domain v1 eval — trading subset gloss + bench KPIs (no core wire edits)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GLOSS_REPORT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_gloss_session_report_v1_latest.json"
BENCH_V0 = ROOT / "reports/finops_wire_bench_v0_latest.json"
HOLDOUT = ROOT / "docs/final/artifacts/finops_wire_bench_holdout_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/finops_wire_domain_v1_eval_latest.json"
PRIMARY = "trading"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_eval() -> dict[str, Any]:
    gloss = _read(GLOSS_REPORT)
    bench = _read(BENCH_V0)
    hold = _read(HOLDOUT)
    summary = (gloss.get("scenario_summary") or {}).get(PRIMARY) or {}
    turns = (gloss.get("turns_by_scenario") or {}).get(PRIMARY) or []

    known_atoms = 0
    total_atoms = 0
    for t in turns:
        for row in t.get("gloss_rows") or []:
            total_atoms += 1
            if row.get("known"):
                known_atoms += 1

    gloss_coverage = (known_atoms / total_atoms) if total_atoms else 0.0
    empty_turns = int(summary.get("empty_turn_count") or 0)
    turn_count = int(summary.get("turn_count") or len(turns))

    packet_ok = bool((bench.get("finops_kpis") or {}).get("packet_roundtrip_ok"))
    schema_ok = bool((bench.get("trading_session") or {}).get("all_envelopes_schema_valid"))

    gates = {
        "gloss_report_ok": gloss.get("ok") is True,
        "bench_v0_ok": bench.get("ok") is True,
        "holdout_ok": hold.get("ok") is True,
        "packet_roundtrip_ok": packet_ok,
        "envelope_schema_valid": schema_ok,
        "no_empty_trading_turns": empty_turns == 0,
        "gloss_known_atom_ratio_min_0_8": gloss_coverage >= 0.8,
    }

    return {
        "ok": all(gates.values()),
        "schema": "finops_wire_domain_v1_eval_v1",
        "generated_at_utc": _utc(),
        "domain_id": "finops_handoff_v1",
        "branch_target": "b-track-finops-wire-v1",
        "primary_scenario": PRIMARY,
        "session_id": (bench.get("trading_session") or {}).get("session_id"),
        "trading_summary": summary,
        "metrics": {
            "turn_count": turn_count,
            "empty_turn_count": empty_turns,
            "gloss_known_atom_ratio": round(gloss_coverage, 4),
            "avg_atom_id_count": summary.get("avg_atom_id_count"),
            "avg_byte_savings_vs_packet": (bench.get("finops_kpis") or {}).get("avg_byte_savings_vs_packet"),
        },
        "gates": gates,
        "disclaimer_ko": bench.get("disclaimer_ko") or hold.get("boundary_ack", ""),
        "sources": {
            "gloss_report": GLOSS_REPORT.relative_to(ROOT).as_posix(),
            "bench_v0": BENCH_V0.relative_to(ROOT).as_posix(),
            "holdout": HOLDOUT.relative_to(ROOT).as_posix(),
        },
        "research_only": True,
        "boundary_ack": "FinOps domain v1 eval on trading fixture; not L1 official close or L2 commercial.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = run_eval()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
