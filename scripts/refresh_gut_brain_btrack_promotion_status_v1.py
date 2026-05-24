#!/usr/bin/env python3
"""Refresh gut_brain_agent_constitution_promotion btrack_numeric_to_track_a block from gates JSON."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATES = ROOT / "reports" / "prophecy_promotion_gates_recommended_chain_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "gut_brain_agent_constitution_promotion_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    o = json.loads(path.read_text(encoding="utf-8"))
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.gates_json.is_file():
        raise SystemExit(f"missing gates: {args.gates_json}")
    gates = _load(args.gates_json)
    doc = _load(args.output) if args.output.is_file() else {}
    if str(doc.get("schema") or "") != "gut_brain_agent_constitution_promotion_v1":
        doc = {
            "schema": "gut_brain_agent_constitution_promotion_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "promotion_layers": {},
        }
    combined = bool(gates.get("combined_all_passed"))
    strict = bool(gates.get("strict_passed"))
    auto = bool(gates.get("auto_promote_ready"))
    outcome = str(gates.get("outcome_class") or "neutral_bucket")
    rec = str(gates.get("promotion_recommendation") or "defer")
    if combined and strict and auto:
        status = "auto_promote_ready"
    elif combined and strict:
        status = "pass_candidate_human_review"
    elif strict or bool(gates.get("soft_passed")):
        status = "soft_or_partial"
    else:
        status = "blocked"
    layers = doc.setdefault("promotion_layers", {})
    if not isinstance(layers, dict):
        layers = {}
        doc["promotion_layers"] = layers
    gates_path = args.gates_json.resolve()
    try:
        evidence_rel = str(gates_path.relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        evidence_rel = str(gates_path).replace("\\", "/")
    layers["btrack_numeric_to_track_a"] = {
        "status": status,
        "evidence_path": evidence_rel,
        "artifacts_ssot": "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json",
        "observed": {
            "combined_all_passed": combined,
            "strict_passed": strict,
            "auto_promote_ready": auto,
            "strict_pass_streak": gates.get("strict_pass_streak"),
            "outcome_class": outcome,
            "promotion_recommendation": rec,
        },
        "required_for_a_track_or_live": [
            "human sign-off (prophecy_release_human_signoff_v1 or manual lock)",
            "no automatic live routing from B-track gates alone",
            "Track A candidate / release checklist if productizing",
        ],
        "note": "Refreshed from ensemble v2 recommended_chain gates; B-track only.",
    }
    doc["generated_at_utc"] = _utc_now()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"btrack_numeric_to_track_a.status={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
