#!/usr/bin/env python3
"""Build consolidated artifact for gpu-04 universal precursor resweep."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_RULESET = ART / "universal_precursor_ruleset_v1_latest.json"
DEFAULT_TUNING = ART / "universal_precursor_gate_tuning_v1_latest.json"
DEFAULT_ROBUST = ART / "universal_precursor_robust_gate_v1_latest.json"
DEFAULT_SUFF = ART / "universal_precursor_sufficiency_v1_latest.json"
DEFAULT_OUT = ART / "gpu_universal_precursor_resweep_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ruleset-json", type=Path, default=DEFAULT_RULESET)
    ap.add_argument("--tuning-json", type=Path, default=DEFAULT_TUNING)
    ap.add_argument("--robust-gate-json", type=Path, default=DEFAULT_ROBUST)
    ap.add_argument("--sufficiency-json", type=Path, default=DEFAULT_SUFF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ruleset = _load(args.ruleset_json)
    tuning = _load(args.tuning_json)
    robust = _load(args.robust_gate_json)
    suff = _load(args.sufficiency_json)

    rec_tuning = tuning.get("recommended_strict_gate") if isinstance(tuning.get("recommended_strict_gate"), dict) else {}
    rec_robust = robust.get("recommended_robust_gate") if isinstance(robust.get("recommended_robust_gate"), dict) else {}
    overall = str(suff.get("overall_decision") or "NOT_YET_SUFFICIENT")

    out = {
        "schema": "gpu_universal_precursor_resweep_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "fact_lock_mode": "numeric_scan_only",
        "inputs": {
            "ruleset_json": str(args.ruleset_json).replace("\\", "/"),
            "tuning_json": str(args.tuning_json).replace("\\", "/"),
            "robust_gate_json": str(args.robust_gate_json).replace("\\", "/"),
            "sufficiency_json": str(args.sufficiency_json).replace("\\", "/"),
        },
        "resweep_summary": {
            "relaxed_intersection_count": int(((ruleset.get("gate") or {}).get("score") or {}).get("count_relaxed_gate", 0)),
            "joined_text_count": int(((ruleset.get("gate") or {}).get("score") or {}).get("count_text_joined", 0)),
            "cluster_count": int(ruleset.get("cluster_count") or 0),
            "recommended_strict_gate": rec_tuning,
            "recommended_robust_gate": rec_robust,
            "sufficiency_overall_decision": overall,
            "sufficiency_pass_count": int(suff.get("pass_count") or 0),
            "sufficiency_total_checks": int(suff.get("total_checks") or 0),
        },
        "status": "go_research_robust" if overall == "SUFFICIENT_RESEARCH" else "hold_research",
        "constraints": {
            "no_auto_live_binding": True,
            "btrack_research_only": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={out['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
