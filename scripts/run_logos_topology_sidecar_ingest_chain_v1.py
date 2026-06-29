#!/usr/bin/env python3
"""Layer A topology sidecar ingest + governance gate chain ([HYPO])."""

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
DEFAULT_INPUT = ROOT / "data/logos/topology_sidecar_job_suffering_hypo_v1.seed.json"
CHAIN_REPORT = ROOT / "reports/logos_topology_sidecar_ingest_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_chain(*, input_path: Path) -> dict[str, Any]:
    from scripts.ingest_logos_topology_sidecar_hypo_v1 import ingest, validate_topology_sidecar, _load_json

    doc = _load_json(input_path)
    pre_errors, pre_cross = validate_topology_sidecar(doc)
    ingest_report = ingest(input_path=input_path, dry_run=False)
    ingested_path = ROOT / ingest_report["output_path"]
    ingested = _load_json(ingested_path)

    gate_errors: list[str] = []
    if ingested.get("schema") != "logos_topology_sidecar_ingested_v1":
        gate_errors.append("ingested schema mismatch")
    if ingested.get("send_gate") != "HOLD":
        gate_errors.append("send_gate not HOLD")
    if ingested.get("track_a_blocked") is not True:
        gate_errors.append("track_a_blocked false")
    if ingested.get("materialize_canon") is not False:
        gate_errors.append("materialize_canon true")
    topo = ingested.get("topology") or {}
    if (topo.get("intentional_causal_gap") or {}).get("why_question_assembled") is not False:
        gate_errors.append("why_question_assembled must stay false")

    ok = not pre_errors and not gate_errors
    chain = {
        "schema": "logos_topology_sidecar_ingest_chain_v1",
        "ok": ok,
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "steps": {
            "validate": {"ok": not pre_errors, "errors": pre_errors, "cross_check_preview": pre_cross},
            "ingest": {"ok": True, **ingest_report},
            "gate": {"ok": not gate_errors, "errors": gate_errors},
        },
        "reproduce": f"py scripts/run_logos_topology_sidecar_ingest_chain_v1.py --input {input_path.relative_to(ROOT).as_posix()}",
    }
    CHAIN_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_REPORT.write_text(json.dumps(chain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return chain


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = ap.parse_args()
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    if not input_path.is_file():
        print(f"Missing input: {input_path}", file=sys.stderr)
        return 2
    chain = run_chain(input_path=input_path)
    print(f"WROTE: {CHAIN_REPORT}")
    print(f"  ok={chain['ok']} send_gate={chain['send_gate']}")
    if not chain["ok"]:
        errs = chain["steps"]["validate"]["errors"] + chain["steps"]["gate"]["errors"]
        print("\n".join(errs), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
