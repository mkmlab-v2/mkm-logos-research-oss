#!/usr/bin/env python3
"""Append B-track parameter-shift rows to effective_adjustments_registry_v1.jsonl (no auto-apply)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs" / "final" / "artifacts" / "effective_adjustments_registry_v1.jsonl"
DEFAULT_SWEEP_SUMMARY = ROOT / "reports" / "prophecy_btrack_recommended_nbps_sweep_v1_latest.json"
DEFAULT_HEADLINE_SWEEP = ROOT / "reports" / "prophecy_headline_deadzone_hold_sweep_v1_latest.json"
DEFAULT_HIT_RATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_eval_latest.json"
OPERATION_MODE_B_UNTIL = "2026-08-14"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _read_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            k = obj.get("adjustment_key")
            if k:
                keys.add(str(k))
    return keys


def _adjustment_key(target: str, value: float) -> str:
    return f"{target}:{value:+.6f}"


def _adjustment_key_pair(min_conf: float, score_dz: float) -> str:
    return f"headline_gates:mc{min_conf:.4f}:dz{score_dz:.4f}"


def _rows_from_sweep(summary: dict[str, Any], *, baseline_accuracy: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = summary.get("rows")
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            nb = float(row["neutral_bps"])
        except (KeyError, TypeError, ValueError):
            continue
        lens_acc = float(row.get("lens_mean_test_accuracy") or 0.0)
        inst_acc = float(row.get("instrument_mean_test_accuracy") or 0.0)
        mean_acc = (lens_acc + inst_acc) / 2.0
        accuracy_delta = round(mean_acc - baseline_accuracy, 6)
        key = _adjustment_key("neutral_bps", nb)
        out.append(
            {
                "schema": "btrack_effective_adjustment_registry_v1",
                "recorded_at_utc": _utc_now(),
                "run_id": f"sweep_{summary.get('generated_at_utc', 'unknown')}",
                "source": "prophecy_btrack_recommended_nbps_sweep_v1",
                "research_only": True,
                "auto_apply_forbidden_until": OPERATION_MODE_B_UNTIL,
                "adjustment_key": key,
                "adjustment": {"target": "neutral_bps", "delta": round(nb, 6)},
                "accuracy_delta": accuracy_delta,
                "metrics": {
                    "lens_mean_test_accuracy": lens_acc,
                    "instrument_mean_test_accuracy": inst_acc,
                    "combined_all_passed": row.get("combined_all_passed"),
                    "soft_passed": row.get("soft_passed"),
                    "promotion_recommendation": row.get("promotion_recommendation"),
                },
            }
        )
    return out


def _rows_from_headline_sweep(sweep_doc: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    chosen = sweep_doc.get("best_passing_50_and_coverage")
    if not isinstance(chosen, dict):
        chosen = sweep_doc.get("best_by_active_hit_rate")
    if not isinstance(chosen, dict):
        return out
    params = chosen.get("params")
    if not isinstance(params, dict):
        return out
    try:
        mc = float(params["min_confidence"])
        dz = float(params["score_abs_deadzone"])
    except (KeyError, TypeError, ValueError):
        return out
    metrics = chosen.get("metrics") if isinstance(chosen.get("metrics"), dict) else {}
    key = _adjustment_key_pair(mc, dz)
    out.append(
        {
            "schema": "btrack_effective_adjustment_registry_v1",
            "recorded_at_utc": _utc_now(),
            "run_id": f"headline_sweep_{sweep_doc.get('generated_at_utc', 'unknown')}",
            "source": "prophecy_headline_deadzone_hold_sweep_v1",
            "research_only": True,
            "auto_apply_forbidden_until": OPERATION_MODE_B_UNTIL,
            "adjustment_key": key,
            "adjustment": {
                "target": "headline_gate_pair",
                "min_confidence_active_gate": round(mc, 6),
                "score_abs_deadzone": round(dz, 6),
            },
            "accuracy_delta": metrics.get("price_directional_hit_rate_active"),
            "metrics": {
                "coverage_active": metrics.get("coverage_active"),
                "passes_both": chosen.get("passes_both"),
            },
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--sweep-summary", type=Path, default=DEFAULT_SWEEP_SUMMARY)
    ap.add_argument("--headline-sweep-json", type=Path, default=DEFAULT_HEADLINE_SWEEP)
    ap.add_argument("--skip-headline-sweep", action="store_true")
    ap.add_argument("--hit-rate-json", type=Path, default=DEFAULT_HIT_RATE)
    ap.add_argument("--baseline-accuracy", type=float, default=0.5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    summary = _load_json(args.sweep_summary)
    if not summary:
        print(f"Missing sweep summary: {args.sweep_summary}", file=__import__("sys").stderr)
        return 2

    hit = _load_json(args.hit_rate_json)
    if hit and isinstance(hit.get("metrics"), dict):
        try:
            hr = float(hit["metrics"].get("price_directional_hit_rate"))
            args.baseline_accuracy = max(args.baseline_accuracy, hr * 0.5)
        except (TypeError, ValueError):
            pass

    candidates = _rows_from_sweep(summary, baseline_accuracy=args.baseline_accuracy)
    if not args.skip_headline_sweep:
        headline = _load_json(args.headline_sweep_json)
        if headline:
            candidates.extend(_rows_from_headline_sweep(headline))
    if not candidates:
        print("No sweep/headline rows to seed.", file=__import__("sys").stderr)
        return 2

    existing = _read_keys(args.registry)
    to_write = [r for r in candidates if r["adjustment_key"] not in existing]
    if args.dry_run:
        print(json.dumps({"would_append": len(to_write), "rows": to_write}, ensure_ascii=False, indent=2))
        return 0

    args.registry.parent.mkdir(parents=True, exist_ok=True)
    with args.registry.open("a", encoding="utf-8") as f:
        for row in to_write:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"WROTE: {args.registry.resolve()} (+{len(to_write)} rows, skipped_existing={len(candidates) - len(to_write)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
