#!/usr/bin/env python3
"""Emit a compact bridge coverage summary from active compression report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ACTIVE_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_GEMATRIA_4D_BRIDGE_EVAL_V1.json"


def main() -> int:
    active = json.loads(ACTIVE_REPORT.read_text(encoding="utf-8"))
    rows = active.get("compression_metrics", {}).get("cases", [])
    total = len(rows)
    with_gem = [r for r in rows if isinstance(r.get("gematria_metadata"), dict)]
    with_bridge = [r for r in rows if isinstance(r.get("gematria_4d_bridge"), dict)]
    mapped = [r for r in with_bridge if r["gematria_4d_bridge"].get("state16") is not None]
    distances = [
        float(r["gematria_4d_bridge"]["distance_to_state16"])
        for r in mapped
        if r["gematria_4d_bridge"].get("distance_to_state16") is not None
    ]
    summary = {
        "schema": "multilens_gematria_4d_bridge_eval_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        "run_config": {
            "include_gematria_metadata": bool(active.get("run_config", {}).get("include_gematria_metadata")),
            "include_gematria_4d_bridge": bool(active.get("run_config", {}).get("include_gematria_4d_bridge")),
        },
        "coverage": {
            "case_count": total,
            "gematria_metadata_cases": len(with_gem),
            "gematria_4d_bridge_cases": len(with_bridge),
            "state16_mapped_cases": len(mapped),
        },
        "bridge_metrics": {
            "avg_distance_to_state16": (sum(distances) / len(distances)) if distances else None,
            "max_distance_to_state16": max(distances) if distances else None,
            "min_distance_to_state16": min(distances) if distances else None,
        },
        "note": "Coverage and distance only; this is not an accuracy uplift proof.",
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
