#!/usr/bin/env python3
"""Build solution planner from coordinator decision pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _plan_for(action: str) -> tuple[list[str], list[str], list[str]]:
    if action == "GO":
        return (
            ["Confirm trend breadth before scaling.", "Use phased entry sizing.", "Re-check if volatility spikes."],
            ["Do not over-leverage.", "Do not ignore risk gates."],
            ["Set strict stop policy.", "Downgrade to WATCH on signal divergence."],
        )
    if action == "HOLD":
        return (
            ["Preserve capital and reduce exposure.", "Wait for evidence refresh.", "Run only monitoring cycle."],
            ["No new aggressive entries.", "No override without human signoff."],
            ["Keep defensive posture.", "Escalate if conflicting signals expand."],
        )
    return (
        ["Prioritize observation over execution.", "Trade only on confirmed triggers.", "Re-evaluate at session close."],
        ["Avoid momentum chasing.", "Avoid discretionary overrides."],
        ["Track risk/opportunity delta.", "Downgrade to HOLD on risk jump."],
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-pack-json", type=Path, default=ART / "three_lens_coordinator_decision_pack_v1_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "three_lens_solution_planner_v1_latest.json")
    args = ap.parse_args()

    in_path = args.decision_pack_json if args.decision_pack_json.is_absolute() else ROOT / args.decision_pack_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    doc = _read_json(in_path)
    action = str((doc.get("final_decision") or {}).get("action") or "WATCH").upper()
    recommended, avoid, mitigations = _plan_for(action)

    payload = {
        "schema": "three_lens_solution_planner_v1",
        "generated_at_utc": _now(),
        "action": action,
        "recommended_actions": recommended,
        "avoid_actions": avoid,
        "risk_mitigations": mitigations,
        "disclaimer": "Decision-support guidance only; not investment, medical, or legal advice.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "action": action}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
