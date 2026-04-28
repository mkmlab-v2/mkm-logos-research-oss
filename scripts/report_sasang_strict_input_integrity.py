#!/usr/bin/env python3
"""Report integrity/coverage status for Sasang strict gate inputs."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_STRICT = ART / "sasang_high_reliability_gate_strict_latest.json"
DEFAULT_STRICT_SHADOW = ART / "sasang_high_reliability_gate_strict_synthetic_calibrated_latest.json"
DEFAULT_OUT = ART / "sasang_strict_input_integrity_latest.json"


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", type=Path, default=DEFAULT_STRICT)
    ap.add_argument("--strict-shadow", type=Path, default=DEFAULT_STRICT_SHADOW)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.strict.is_file():
        print(f"ERROR: missing strict gate artifact: {args.strict}")
        return 2

    strict = _jread(args.strict)
    shadow = _jread(args.strict_shadow) if args.strict_shadow.is_file() else None

    s = strict.get("snapshot") or {}
    paired_rows = int(s.get("paired_rows") or 0)
    recall_macro = float(s.get("recall_macro") or 0.0)
    ece = float(s.get("ece") or 1.0)
    brier = float(s.get("brier_score") or 1.0)
    strict_decision = str(strict.get("decision") or "UNKNOWN").upper()
    shadow_decision = str((shadow or {}).get("decision") or "MISSING").upper()

    root_cause = "NONE"
    if paired_rows < 128:
        root_cause = "production_paired_rows_insufficient"
    elif recall_macro < 0.75:
        root_cause = "production_recall_insufficient"
    elif ece > 0.10:
        root_cause = "production_calibration_ece_high"
    elif brier > 0.15:
        root_cause = "production_calibration_brier_high"

    report = {
        "schema": "sasang_strict_input_integrity_v1",
        "generated_at_utc": _now(),
        "strict_artifact": str(args.strict.resolve()),
        "strict_shadow_artifact": str(args.strict_shadow.resolve()) if args.strict_shadow.is_file() else None,
        "production_snapshot": {
            "decision": strict_decision,
            "paired_rows": paired_rows,
            "recall_macro": recall_macro,
            "ece": ece,
            "brier_score": brier,
        },
        "shadow_snapshot": {
            "decision": shadow_decision,
        },
        "integrity": {
            "production_strict_pass": strict_decision == "PASS",
            "shadow_strict_pass": shadow_decision == "PASS",
            "root_cause": root_cause,
            "authoritative_for_promotion": strict_decision == "PASS",
        },
        "policy": {
            "shadow_only_not_authoritative": True,
            "track_b_to_a_autobind_forbidden": True,
            "human_signoff_required": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"root_cause={root_cause}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
