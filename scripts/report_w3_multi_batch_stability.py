#!/usr/bin/env python3
"""Build stability summary from W3 batch results V2/V3/V4."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "W3_MULTI_BATCH_STABILITY_SUMMARY_V1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    runs = []
    for idx in (2, 3, 4):
        p = ART / f"W3_RESONANCE_BATCH_RESULT_V{idx}.json"
        d = _load(p)
        fs = d.get("falsification_summary") or {}
        pg = d.get("promotion_gate") or {}
        runs.append(
            {
                "variant": f"V{idx}",
                "path": str(p).replace("\\", "/"),
                "promotion_gate_passed": bool(pg.get("passed", False)),
                "false_equivalence_risk_count": int(fs.get("false_equivalence_risk_count", 0)),
                "deterministic_wording_risk_count": int(fs.get("deterministic_wording_risk_count", 0)),
            }
        )

    false_vals = [r["false_equivalence_risk_count"] for r in runs]
    det_vals = [r["deterministic_wording_risk_count"] for r in runs]
    out = {
        "schema": "w3_multi_batch_stability_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs": runs,
        "aggregate": {
            "all_passed": all(r["promotion_gate_passed"] for r in runs),
            "false_equivalence_avg": round(mean(false_vals), 6),
            "false_equivalence_max": max(false_vals) if false_vals else 0,
            "deterministic_wording_avg": round(mean(det_vals), 6),
            "deterministic_wording_max": max(det_vals) if det_vals else 0,
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: W3 stability summary generated")
    print(f"out={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
