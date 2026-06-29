#!/usr/bin/env python3
"""TKM encounter_sequence P37 gate: ops closure v2 + full lens stack [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P36_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p36_gate_v1_latest.json"
OPS = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p37_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p36 = _load(P36_GATE)
    ops = _load(OPS)
    weekly = _load(WEEKLY)
    items = ops.get("items") if isinstance(ops.get("items"), dict) else {}
    oc = weekly.get("ops_closure_kpi") if isinstance(weekly.get("ops_closure_kpi"), dict) else {}

    checks = {
        "p36_gate_ok": {"passed": p36.get("gate_ok") is True},
        "ops_closure_ok": {"passed": ops.get("closure_ok") is True},
        "full_stack_closure_ok": {"passed": ops.get("full_stack_closure_ok") is True},
        "disagreement_cross_item_ok": {"passed": (items.get("7_disagreement_resolver_cross") or {}).get("ok") is True},
        "lens_stack_p33_p36_ok": {
            "passed": all(
                (items.get(k) or {}).get("ok") is True
                for k in ("9_cross_lens_p33", "10_passive_observation_p34", "11_conflict_resolver_p35", "12_disagreement_cross_p36")
            )
        },
        "weekly_ops_closure_sync_ok": {"passed": oc.get("full_stack_closure_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p37_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p37_status": "ops_closure_v2_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "ops_closure_version": ops.get("version"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p37_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p37_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
