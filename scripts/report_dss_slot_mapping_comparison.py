#!/usr/bin/env python3
"""Compare full vs canonical-only DSS slot mapping KPIs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_latest.json"
CANON = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_canonical_latest.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_comparison_latest.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    full = _load(FULL)
    canon = _load(CANON)
    fk = full.get("kpi", {})
    ck = canon.get("kpi", {})
    out = {
        "schema": "btrack_dss_direct_slot_mapping_comparison_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "full_kpi": fk,
        "canonical_kpi": ck,
        "delta": {
            "mean_confidence_boost": float(ck.get("mean_confidence_boost", 0.0)) - float(fk.get("mean_confidence_boost", 0.0)),
            "traceability_rate": float(ck.get("traceability_rate", 0.0)) - float(fk.get("traceability_rate", 0.0)),
            "slot_coverage_rate": float(ck.get("slot_coverage_rate", 0.0)) - float(fk.get("slot_coverage_rate", 0.0)),
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
