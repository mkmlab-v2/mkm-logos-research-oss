#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build final submission Go/No-Go decision artifact.")
    ap.add_argument("--checklist-json", default="docs/final/artifacts/two_track_submission_checklist_latest.json")
    ap.add_argument("--evidence-json", default="docs/final/artifacts/two_track_submission_evidence_bundle_latest.json")
    ap.add_argument("--fail-boundary-gate-json", default="docs/final/artifacts/two_track_fail_boundary_gate_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/two_track_submission_go_nogo_latest.json")
    args = ap.parse_args()

    cp = resolve(args.checklist_json)
    ep = resolve(args.evidence_json)
    gp = resolve(args.fail_boundary_gate_json)
    op = resolve(args.output_json)
    for p in (cp, ep, gp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    checklist = load(cp)
    evidence = load(ep)
    gate = load(gp)

    submission_ready = bool(checklist.get("submission_ready", False))
    gates = evidence.get("gates") if isinstance(evidence.get("gates"), dict) else {}
    bundle_ready = bool(gates.get("bundle_ready", False))
    publication_ready = bool(gates.get("ready_for_publication_claim", False))
    gate_eval = gate.get("gate_eval") if isinstance(gate.get("gate_eval"), dict) else {}
    should_trade = bool(gate_eval.get("should_trade", False))
    rollback = bool(gate_eval.get("rollback", True))

    go = submission_ready and bundle_ready and publication_ready and (should_trade and not rollback)
    reasons = []
    if not submission_ready:
        reasons.append("submission_checklist_not_ready")
    if not bundle_ready:
        reasons.append("evidence_bundle_not_ready")
    if not publication_ready:
        reasons.append("publication_claim_not_ready")
    if rollback:
        reasons.append("fail_boundary_gate_requests_rollback")
    if not should_trade:
        reasons.append("fail_boundary_gate_not_go")

    out = {
        "schema": "two_track_submission_go_nogo_v1",
        "generated_at_utc": now(),
        "inputs": {
            "checklist_json": str(cp),
            "evidence_json": str(ep),
            "fail_boundary_gate_json": str(gp),
        },
        "decision": {
            "go": go,
            "status": "GO" if go else "NO_GO",
            "reasons": reasons,
        },
        "snapshot": {
            "submission_ready": submission_ready,
            "bundle_ready": bundle_ready,
            "ready_for_publication_claim": publication_ready,
            "fail_boundary_should_trade": should_trade,
            "fail_boundary_rollback": rollback,
        },
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

