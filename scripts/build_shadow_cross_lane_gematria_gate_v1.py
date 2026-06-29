#!/usr/bin/env python3
"""Gate for cross-lane gematria audit isolation and completeness [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports/shadow_cross_lane_gematria_audit_v1_latest.json"
XREF = ROOT / "reports/shadow_canon_gematria_xref_map_v1_latest.json"
BRIDGE = ROOT / "reports/shadow_appendix_id_bridge_v1_latest.json"
WITNESS_MAP = ROOT / "reports/dss_11q5_line_witness_map_v1_latest.json"
WITNESS_REGISTRY = ROOT / "reports/shadow_line_witness_registry_v1_latest.json"
GATE_P1 = ROOT / "docs/final/artifacts/shadow_lane_gematria_gate_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/shadow_cross_lane_gematria_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build() -> dict[str, Any]:
    audit = _load(AUDIT)
    xref = _load(XREF)
    bridge = _load(BRIDGE)
    witness_map = _load(WITNESS_MAP)
    witness_registry = _load(WITNESS_REGISTRY)
    p1_gate = _load(GATE_P1)
    xref_sm = xref.get("summary") or {}
    audit_sm = audit.get("summary") or {}
    bridge_sm = bridge.get("summary") or {}
    witness_sm = witness_registry.get("summary") or {}

    checks = {
        "p1_isolation_gate_ok": {"passed": p1_gate.get("gate_ok") is True},
        "xref_samples_resolved": {
            "passed": int(xref_sm.get("resolved_shadow_samples") or 0) >= 9,
            "resolved_shadow_samples": xref_sm.get("resolved_shadow_samples"),
        },
        "bridge_dss_enriched_coverage": {
            "passed": int(bridge_sm.get("dss_enriched_appendix_hits") or 0) >= 130,
            "hits": bridge_sm.get("dss_enriched_appendix_hits"),
            "total": bridge_sm.get("dss_enriched_rows"),
        },
        "witness_map_entry_12_13": {
            "passed": int((witness_map.get("summary") or {}).get("targets") or 0) >= 2,
            "targets": (witness_map.get("summary") or {}).get("targets"),
        },
        "line_witness_registry": {
            "passed": int(witness_sm.get("numeric_comparison_eligible_rows") or 0) >= 4,
            "numeric_eligible_rows": witness_sm.get("numeric_comparison_eligible_rows"),
        },
        "audit_pilot_complete": {
            "passed": int(audit_sm.get("pilot_verses") or 0) >= 9,
            "pilot_verses": audit_sm.get("pilot_verses"),
        },
        "audit_line_witness_numeric": {
            "passed": int(audit_sm.get("line_witness_numeric_eligible_samples") or 0) >= 4,
            "line_witness_numeric_eligible_samples": audit_sm.get("line_witness_numeric_eligible_samples"),
        },
        "audit_flags": {
            "passed": audit.get("audit_only") is True and audit.get("theology_to_sales_forbidden") is True,
            "send_gate": audit.get("send_gate"),
        },
        "track_wall": {
            "passed": (audit.get("track_wall") or {}).get("merge_into_canon_31k_41k") is False,
        },
    }
    gate_ok = all(c.get("passed") for c in checks.values())

    return {
        "schema": "shadow_cross_lane_gematria_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "gate_ok": gate_ok,
        "checks": checks,
        "numeric_comparison_note": (
            "metadata_only_samples may be >0 while gate_ok; pilot honesty requires reporting "
            "non-eligible citations separately from Hebrew witness deltas."
        ),
        "reproduce": "py scripts/build_shadow_cross_lane_gematria_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "gate_ok": doc["gate_ok"]}, ensure_ascii=False))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
