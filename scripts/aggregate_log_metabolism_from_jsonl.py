#!/usr/bin/env python3
"""Aggregate domain-neutral log metabolism scalars from JSONL cohort rows.

Reads optional inference_config_v1.json for primary_keys + aliases.
Outputs summary JSON: counts, means, ratio proxy (mean throttle / mean egress), optional phase_proxy vs thresholds.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "docs" / "final" / "artifacts" / "inference_config_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_float(row: dict[str, Any], primary: str, aliases: list[str]) -> float | None:
    keys = [primary] + [a for a in aliases if a != primary]
    for k in keys:
        if k not in row:
            continue
        v = row[k]
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            return float(v)
    return None


def aggregate_rows(
    rows: list[dict[str, Any]],
    *,
    egress_key: str,
    throttle_key: str,
    egress_aliases: list[str],
    throttle_aliases: list[str],
    high_egress: float,
    high_persistence: float,
) -> dict[str, Any]:
    egress_vals: list[float] = []
    throttle_vals: list[float] = []
    skipped = 0
    for row in rows:
        e = _pick_float(row, egress_key, egress_aliases)
        t = _pick_float(row, throttle_key, throttle_aliases)
        if e is None or t is None:
            skipped += 1
            continue
        egress_vals.append(e)
        throttle_vals.append(t)

    n = len(egress_vals)
    if n == 0:
        return {
            "row_count_valid": 0,
            "row_count_skipped": skipped,
            "error": "no_valid_rows",
        }

    def _pct(xs: list[float], p: float) -> float:
        xs = sorted(xs)
        if not xs:
            return 0.0
        k = (len(xs) - 1) * p / 100.0
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(xs[int(k)])
        return float(xs[f] * (c - k) + xs[c] * (k - f))

    mean_e = statistics.mean(egress_vals)
    mean_t = statistics.mean(throttle_vals)
    ratio_metabolism: float | None = (mean_e / mean_t) if mean_t > 1e-12 else None
    high_windows = sum(
        1
        for e, t in zip(egress_vals, throttle_vals)
        if e >= high_egress * max(mean_e, 1e-9)
        or (mean_t > 1e-12 and t >= high_persistence * max(mean_t, 1e-9))
    )

    out: dict[str, Any] = {
        "row_count_valid": n,
        "row_count_skipped": skipped,
        "egress_pressure": {
            "mean": mean_e,
            "p95": _pct(egress_vals, 95),
            "max": max(egress_vals),
        },
        "throttle_events": {
            "mean": mean_t,
            "p95": _pct(throttle_vals, 95),
            "max": max(throttle_vals),
        },
        "ratio_metabolism_mean_egress_over_mean_throttle": ratio_metabolism,
        "windows_above_relaxed_threshold_count": high_windows,
        "thresholds_used": {"high_egress": high_egress, "high_persistence": high_persistence},
    }
    if ratio_metabolism is None:
        out["ratio_metabolism_note"] = "mean_throttle_near_zero; ratio omitted (JSON-safe)."
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate log metabolism JSONL cohort (neutral field names).")
    ap.add_argument("--in", dest="inp", type=Path, required=True, help="Input .jsonl path")
    ap.add_argument("--out", type=Path, required=True, help="Output summary JSON")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="inference_config_v1.json (optional)")
    args = ap.parse_args()

    inp = Path(args.inp).resolve()
    if not inp.is_file():
        print(f"FAIL: input not found {inp}", file=sys.stderr)
        return 1

    rows: list[dict[str, Any]] = []
    with inp.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    egress_key = "egress_pressure"
    throttle_key = "throttle_events"
    egress_aliases: list[str] = []
    throttle_aliases: list[str] = []
    high_egress = 0.75
    high_persistence = 0.75
    cfg_path = Path(args.config).resolve()
    if cfg_path.is_file():
        cfg = _load_json(cfg_path)
        mj = cfg.get("metabolism_jsonl") or {}
        pk = mj.get("primary_keys") or {}
        egress_key = str(pk.get("egress_pressure") or egress_key)
        throttle_key = str(pk.get("throttle_events") or throttle_key)
        al = mj.get("aliases") or {}
        egress_aliases = [str(x) for x in (al.get("egress_pressure") or [])]
        throttle_aliases = [str(x) for x in (al.get("throttle_events") or [])]
        th = cfg.get("metabolism_thresholds") or {}
        high_egress = float(th.get("high_egress", high_egress))
        high_persistence = float(th.get("high_persistence", high_persistence))

    summary = aggregate_rows(
        rows,
        egress_key=egress_key,
        throttle_key=throttle_key,
        egress_aliases=egress_aliases,
        throttle_aliases=throttle_aliases,
        high_egress=high_egress,
        high_persistence=high_persistence,
    )

    try:
        src_rel = str(inp.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        src_rel = str(inp)

    payload = {
        "schema": "log_metabolism_aggregate_summary_v1",
        "source_jsonl": src_rel,
        "summary": summary,
    }

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} valid_rows={summary.get('row_count_valid', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
