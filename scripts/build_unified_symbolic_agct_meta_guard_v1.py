#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.89, K:0.71, M:0.49}
# Balance: 90
# Purpose: Build unified final meta guard from AGCT runtime guard and symbolic shadow gate.
# Keywords: meta-guard, agct, symbolic, hold, pass, governance
"""Build unified meta guard decision (AGCT + symbolic)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build unified symbolic+AGCT meta guard.")
    ap.add_argument(
        "--agct-runtime-stub-json",
        type=Path,
        default=Path("reports/agct_sasang_size_overlay_runtime_stub_v1_latest.json"),
    )
    ap.add_argument(
        "--symbolic-shadow-gate-json",
        type=Path,
        default=Path("reports/symbolic_math_mapping_shadow_gate_v1_latest.json"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/unified_symbolic_agct_meta_guard_v1_latest.json"),
    )
    ns = ap.parse_args()

    agct = _load_json(ns.agct_runtime_stub_json)
    symbolic = _load_json(ns.symbolic_shadow_gate_json)

    agct_guard = agct.get("holdout_runtime_guard_v1", {})
    agct_pass = bool(agct_guard.get("guard_pass"))
    agct_enabled = bool(agct.get("runtime_stub", {}).get("enabled"))
    agct_status = str(agct.get("runtime_stub", {}).get("status") or "UNKNOWN")

    symbolic_decision = str(symbolic.get("decision") or "UNKNOWN")
    symbolic_pass = symbolic_decision == "PASS_SHADOW_STABLE"

    final_pass = agct_pass and symbolic_pass
    final_decision = "PASS_UNIFIED_META_GUARD" if final_pass else "HOLD_UNIFIED_META_GUARD"

    payload = {
        "schema": "unified_symbolic_agct_meta_guard_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
            "rule": "If either AGCT guard or symbolic shadow gate is HOLD, final decision is HOLD.",
        },
        "inputs": {
            "agct_runtime_stub_json": str(ns.agct_runtime_stub_json.resolve()),
            "symbolic_shadow_gate_json": str(ns.symbolic_shadow_gate_json.resolve()),
        },
        "components": {
            "agct": {
                "guard_pass": agct_pass,
                "runtime_enabled": agct_enabled,
                "runtime_status": agct_status,
            },
            "symbolic": {
                "shadow_pass": symbolic_pass,
                "shadow_decision": symbolic_decision,
            },
        },
        "decision": final_decision,
    }

    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out.resolve()} decision={final_decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
