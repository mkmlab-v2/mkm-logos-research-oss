# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.6, L:0.9, K:0.8, M:0.7}
# Balance: 88
# Purpose: Export DSS confidence calibration log artifact.
# Keywords: calibration, confidence, dss, btrack, artifact
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
FULL = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_latest.json"
CANON = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_direct_slot_mapping_canonical_latest.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_confidence_calibration_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    full = _load(FULL)
    canon = _load(CANON)

    fk = full.get("kpi", {})
    ck = canon.get("kpi", {})
    params = full.get("inputs", {}).get("confidence_params", {})
    mode = full.get("inputs", {}).get("confidence_mode", "unknown")

    payload = {
        "schema": "btrack_dss_confidence_calibration_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confidence_mode": mode,
        "confidence_params": params,
        "target_mean_confidence_boost": 0.8,
        "full": {
            "mean_confidence_boost": float(fk.get("mean_confidence_boost", 0.0)),
            "mean_confidence_boost_base": float(fk.get("mean_confidence_boost_base", 0.0)),
            "target_ok": bool(fk.get("target_mean_confidence_boost_ok", False)),
        },
        "canonical_only": {
            "mean_confidence_boost": float(ck.get("mean_confidence_boost", 0.0)),
            "mean_confidence_boost_base": float(ck.get("mean_confidence_boost_base", 0.0)),
            "target_ok": bool(ck.get("target_mean_confidence_boost_ok", False)),
        },
        "decision": {
            "promote_v2": bool(fk.get("target_mean_confidence_boost_ok", False))
            and bool(ck.get("target_mean_confidence_boost_ok", False)),
            "note": "promote only if both full and canonical meet target",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
