# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.88, K:0.35, M:0.52}
# Balance: 90
# Purpose: Combine operational and sasang clinical bootstrap metrics into final reliability gate.
# Keywords: sasang, reliability, gate, calibration, brier, recall
#!/usr/bin/env python3
"""Generate sasang high-reliability gate report (PASS/HOLD)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OPS_GATE = ROOT / "docs" / "final" / "artifacts" / "high_reliability_mode_gate_latest.json"
DEFAULT_CLINICAL = (
    ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_clinical_eval_from_btrack_eval_full_mapped_latest.json"
)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "sasang_high_reliability_gate_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops-gate", default=str(DEFAULT_OPS_GATE))
    ap.add_argument("--clinical", default=str(DEFAULT_CLINICAL))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument(
        "--profile",
        choices=("standard", "strict"),
        default="standard",
        help="Gate profile: standard (default) or strict.",
    )
    ap.add_argument("--min-paired-rows", type=int, default=64)
    ap.add_argument("--min-recall-macro", type=float, default=0.65)
    ap.add_argument("--max-ece", type=float, default=0.20)
    ap.add_argument("--max-brier", type=float, default=0.25)
    args = ap.parse_args()

    ops_path = _abs(args.ops_gate)
    clinical_path = _abs(args.clinical)
    out_path = _abs(args.out)
    for p in (ops_path, clinical_path):
        if not p.is_file():
            print(f"ERROR: missing required file: {p}")
            return 2

    ops = _jread(ops_path)
    clinical = _jread(clinical_path)

    # Strict mode tightens calibration/recall gates for higher-confidence operation.
    min_paired_rows = int(args.min_paired_rows)
    min_recall_macro = float(args.min_recall_macro)
    max_ece = float(args.max_ece)
    max_brier = float(args.max_brier)
    if args.profile == "strict":
        min_paired_rows = max(min_paired_rows, 128)
        min_recall_macro = max(min_recall_macro, 0.75)
        max_ece = min(max_ece, 0.10)
        max_brier = min(max_brier, 0.15)

    paired_rows = int(clinical.get("diagnostics", {}).get("paired_rows", 0) or 0)
    recall_macro = _f(clinical.get("metrics", {}).get("recall_macro"))
    ece = _f(clinical.get("metrics", {}).get("confidence", {}).get("ece"))
    brier = _f(clinical.get("metrics", {}).get("confidence", {}).get("brier_score"))

    checks = {
        "ops_gate_pass": str(ops.get("decision", "")).upper() == "PASS",
        "paired_rows_gte_threshold": paired_rows >= min_paired_rows,
        "recall_macro_gte_threshold": recall_macro is not None and recall_macro >= min_recall_macro,
        "ece_lte_threshold": ece is not None and ece <= max_ece,
        "brier_lte_threshold": brier is not None and brier <= max_brier,
    }
    gaps = {
        "paired_rows_shortfall": max(0, min_paired_rows - paired_rows),
        "recall_macro_shortfall": max(0.0, min_recall_macro - (recall_macro if recall_macro is not None else 0.0)),
        "ece_excess": max(0.0, (ece if ece is not None else 1.0) - max_ece),
        "brier_excess": max(0.0, (brier if brier is not None else 1.0) - max_brier),
    }

    decision = "PASS" if all(checks.values()) else "HOLD"
    report = {
        "schema": "sasang_high_reliability_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"ops_gate": str(ops_path), "clinical_eval": str(clinical_path)},
        "profile": args.profile,
        "thresholds": {
            "min_paired_rows": min_paired_rows,
            "min_recall_macro": min_recall_macro,
            "max_ece": max_ece,
            "max_brier": max_brier,
        },
        "snapshot": {
            "paired_rows": paired_rows,
            "recall_macro": recall_macro,
            "ece": ece,
            "brier_score": brier,
        },
        "checks": checks,
        "gaps": gaps,
        "decision": decision,
        "mode": "sasang_high_reliability_enabled" if decision == "PASS" else "sasang_high_reliability_hold",
        "notes": [
            "This gate is operational quality control, not a medical diagnosis claim.",
            "Final clinical validity still depends on verified real-world GT and governance approval.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path}")
    print(f"decision={decision}")
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

