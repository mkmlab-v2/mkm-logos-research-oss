#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.87, K:0.66, M:0.5}
# Balance: 89
# Purpose: Enforce holdout-based safety guard on AGCT-Sasang runtime stub.
# Keywords: agct, sasang, holdout, guard, runtime, safety
"""Enforce holdout safety guard on AGCT-Sasang runtime stub."""

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
    ap = argparse.ArgumentParser(description="Enforce holdout guard on AGCT-Sasang runtime stub.")
    ap.add_argument("--runtime-stub-json", type=Path, required=True)
    ap.add_argument("--holdout-eval-json", type=Path, required=True)
    ap.add_argument("--min-holdout-accuracy", type=float, default=0.50)
    ap.add_argument("--max-generalization-gap", type=float, default=0.40)
    ap.add_argument("--max-holdout-pvalue", type=float, default=0.20)
    ap.add_argument("--min-holdout-n", type=int, default=30)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Defaults to in-place update on --runtime-stub-json",
    )
    ns = ap.parse_args()

    runtime = _load_json(ns.runtime_stub_json)
    holdout = _load_json(ns.holdout_eval_json)

    results = holdout.get("results", {})
    split = holdout.get("split", {})
    holdout_n = int(split.get("holdout_n") or 0)
    hold_acc_raw = results.get("holdout_accuracy_under_train_mapping")
    hold_acc = float(hold_acc_raw) if hold_acc_raw is not None else 0.0
    gap_raw = results.get("generalization_gap")
    gap = float(gap_raw) if gap_raw is not None else 1.0
    p_raw = results.get("holdout_accuracy_permutation_p_value")
    p_val = float(p_raw) if p_raw is not None else 1.0

    checks = {
        "holdout_sample_size_gate": holdout_n >= int(ns.min_holdout_n),
        "holdout_accuracy_gate": hold_acc >= float(ns.min_holdout_accuracy),
        "generalization_gap_gate": gap <= float(ns.max_generalization_gap),
        "holdout_pvalue_gate": p_val <= float(ns.max_holdout_pvalue),
    }
    guard_pass = all(checks.values())

    rt = runtime.setdefault("runtime_stub", {})
    prev_enabled = bool(rt.get("enabled"))
    prev_status = str(rt.get("status") or "UNKNOWN")

    if not guard_pass:
        rt["enabled"] = False
        rt["status"] = "HOLD_BY_GENERALIZATION_GUARD"
    else:
        # preserve current enabled flag; just annotate pass
        rt["status"] = "READY_FOR_SHADOW_GUARD_PASS" if prev_enabled else "READY_FOR_SHADOW_DISABLED_GUARD_PASS"

    runtime["holdout_runtime_guard_v1"] = {
        "applied_at_utc": _utc_now(),
        "source_holdout_eval_json": str(ns.holdout_eval_json.resolve()),
        "thresholds": {
            "min_holdout_n": int(ns.min_holdout_n),
            "min_holdout_accuracy": float(ns.min_holdout_accuracy),
            "max_generalization_gap": float(ns.max_generalization_gap),
            "max_holdout_pvalue": float(ns.max_holdout_pvalue),
        },
        "checks": checks,
        "guard_pass": guard_pass,
        "observations": {
            "holdout_n": holdout_n,
            "holdout_accuracy_under_train_mapping": hold_acc,
            "generalization_gap": gap,
            "holdout_accuracy_permutation_p_value": p_val,
        },
        "runtime_before": {"enabled": prev_enabled, "status": prev_status},
        "runtime_after": {"enabled": bool(rt.get("enabled")), "status": str(rt.get("status"))},
    }

    out = ns.output_json if ns.output_json is not None else ns.runtime_stub_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out.resolve()} guard_pass={guard_pass} "
        f"hold_acc={hold_acc:.4f} gap={gap:.4f} p={p_val:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
