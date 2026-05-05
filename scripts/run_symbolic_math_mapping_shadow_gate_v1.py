#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.88, K:0.7, M:0.47}
# Balance: 90
# Purpose: Evaluate symbolic mapping stability on shadow stream and emit PASS/HOLD.
# Keywords: symbolic, shadow, gate, drift, mapping, stability
"""Run symbolic math mapping shadow gate v1."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _l2(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def _mapping_loss(a: list[float], b: list[float], w_dist: float, w_consistency: float) -> float:
    cons = abs(_mean(a) - _mean(b))
    return (w_dist * _l2(a, b)) + (w_consistency * cons)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_stream(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Symbolic mapping shadow stability gate.")
    ap.add_argument(
        "--fit-json",
        type=Path,
        default=Path("reports/symbolic_math_mapping_fit_v1_latest.json"),
    )
    ap.add_argument(
        "--stream-jsonl",
        type=Path,
        default=Path("tests/fixtures/symbolic_mapping_shadow_stream_v1.jsonl"),
    )
    ap.add_argument("--max-mean-loss", type=float, default=0.08)
    ap.add_argument("--max-drift", type=float, default=0.03, help="Max absolute delta between first-half and second-half mean loss.")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/symbolic_math_mapping_shadow_gate_v1_latest.json"),
    )
    ns = ap.parse_args()

    fit = _load_json(ns.fit_json)
    stream = _load_stream(ns.stream_jsonl)
    if not stream:
        raise SystemExit("Empty shadow stream.")

    weights = fit.get("summary", {}).get("best_weights", {})
    w_dist = float(weights.get("w_dist", 0.7))
    w_cons = float(weights.get("w_consistency", 0.3))

    losses: list[float] = []
    for row in stream:
        a = row.get("source_vec4d")
        b = row.get("target_vec4d")
        if not (isinstance(a, list) and isinstance(b, list) and len(a) == 4 and len(b) == 4):
            continue
        losses.append(_mapping_loss([float(x) for x in a], [float(x) for x in b], w_dist, w_cons))
    if not losses:
        raise SystemExit("No valid stream rows with 4D vectors.")

    n = len(losses)
    cut = max(1, n // 2)
    first = losses[:cut]
    second = losses[cut:]
    mean_loss = sum(losses) / n
    first_mean = sum(first) / len(first)
    second_mean = sum(second) / len(second) if second else first_mean
    drift = abs(second_mean - first_mean)

    checks = {
        "mean_loss_gate": mean_loss <= float(ns.max_mean_loss),
        "drift_gate": drift <= float(ns.max_drift),
    }
    gate_pass = all(checks.values())

    payload = {
        "schema": "symbolic_math_mapping_shadow_gate_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "fit_json": str(ns.fit_json.resolve()),
            "stream_jsonl": str(ns.stream_jsonl.resolve()),
            "weights": {"w_dist": w_dist, "w_consistency": w_cons},
        },
        "metrics": {
            "sample_count": n,
            "mean_loss": mean_loss,
            "first_half_mean_loss": first_mean,
            "second_half_mean_loss": second_mean,
            "drift_abs": drift,
        },
        "thresholds": {
            "max_mean_loss": float(ns.max_mean_loss),
            "max_drift": float(ns.max_drift),
        },
        "checks": checks,
        "decision": "PASS_SHADOW_STABLE" if gate_pass else "HOLD_SHADOW_UNSTABLE",
    }

    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out.resolve()} decision={payload['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
