#!/usr/bin/env python3
"""Activate Step-5 veto-only candidate with explicit human approval."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
STEP5 = ART / "sasang_12state_promotion_decision_step5_latest.json"
APPROVAL_JSON = ART / "sasang_12state_human_approval_step5_latest.json"
OUT = ART / "sasang_12state_promotion_decision_step5_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--approver", required=True)
    ap.add_argument("--note", default="Human approved veto-only activation after step3/step4 evidence review.")
    args = ap.parse_args()

    gate = _safe_json(STEP5)
    if not gate:
        raise SystemExit(f"missing step5 artifact: {STEP5}")
    if str(gate.get("schema")) != "sasang_12state_promotion_decision_step5_v1":
        raise SystemExit("invalid step5 schema")
    current = str(gate.get("decision", ""))
    if current != "GATING_VETO_ONLY_CANDIDATE":
        raise SystemExit(f"decision '{current}' is not eligible for veto-only activation")

    ts = _now_utc()
    approval = {
        "schema": "sasang_12state_human_approval_step5_v1",
        "approved": True,
        "approved_at_utc": ts,
        "approver": args.approver,
        "approval_note": args.note,
        "input_decision": current,
    }
    APPROVAL_JSON.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gate["decision"] = "GATING_VETO_ONLY_ACTIVE_WITH_HUMAN_APPROVAL"
    gate["human_review_gate_required"] = False
    gate["auto_bridge_allowed"] = False
    gate["approved_at_utc"] = ts
    gate["approved_by"] = args.approver
    gate["human_approval_ref"] = str(APPROVAL_JSON).replace("\\", "/")
    gate["next_step"] = "Veto-only gating is active by human approval; directional auto-bridge remains forbidden."
    OUT.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {APPROVAL_JSON}")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
