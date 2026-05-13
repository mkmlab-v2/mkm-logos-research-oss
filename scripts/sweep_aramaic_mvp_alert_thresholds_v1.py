#!/usr/bin/env python3
"""Grid-search conflict alert/critical thresholds and streak_min on audit log tail."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1])


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_alert_eval_mod():
    path = ROOT / "scripts" / "alert_aramaic_mvp_trend_v1.py"
    spec = importlib.util.spec_from_file_location("_aramaic_mvp_trend_alert_impl", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load alert_aramaic_mvp_trend_v1")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _score_proxy(
    *,
    severity: str,
    streak_len: int,
    conflict_alert: float,
    conflict_critical: float,
    streak_min: int,
) -> float:
    """Higher = calmer defaults (prefer ok, higher thresholds, shorter hot streaks)."""
    tier = {"ok": 1000.0, "alert": 400.0, "critical": 120.0}.get(severity, 0.0)
    return (
        tier
        + 55.0 * float(conflict_alert)
        + 12.0 * float(conflict_critical)
        - 8.0 * float(streak_len)
        - 3.0 * float(streak_min)
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit-jsonl", default="reports/ops/aramaic_mvp_run_audit_log.jsonl")
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/aramaic_mvp_alert_threshold_sweep_latest.json",
    )
    ap.add_argument("--window", type=int, default=50, help="Tail rows (default 50)")
    a = ap.parse_args()

    audit_path = Path(a.audit_jsonl)
    if not audit_path.is_absolute():
        audit_path = ROOT / audit_path
    out_path = Path(a.output_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    mod = _load_alert_eval_mod()
    load_rows = getattr(mod, "_load_audit_rows")
    evaluate = getattr(mod, "evaluate_audit_tail_for_thresholds")

    window_n = max(1, int(a.window))
    all_rows = load_rows(audit_path)
    tail = all_rows[-window_n:] if all_rows else []

    alert_grid = [0.08, 0.10, 0.12, 0.15, 0.18]
    streak_grid = [2, 3, 4, 5]
    rows_out: list[dict[str, Any]] = []

    for sm in streak_grid:
        for ca in alert_grid:
            for delta in (0.12, 0.16, 0.20):
                cc = float(ca) + float(delta)
                if cc >= 0.99:
                    continue
                try:
                    ev = evaluate(tail, alert_thr=ca, critical_thr=cc, streak_min=sm)
                except ValueError:
                    continue
                sev = str(ev["severity"])
                sl = int(ev["streak_len"])
                mx = int(ev["max_level_in_streak"])
                sp = _score_proxy(
                    severity=sev,
                    streak_len=sl,
                    conflict_alert=ca,
                    conflict_critical=cc,
                    streak_min=sm,
                )
                rows_out.append(
                    {
                        "conflict_alert": ca,
                        "conflict_critical": cc,
                        "streak_min": sm,
                        "end_severity": sev,
                        "end_streak_len": sl,
                        "max_level_in_streak": mx,
                        "score_proxy": round(sp, 6),
                    }
                )

    rows_out.sort(key=lambda r: float(r["score_proxy"]), reverse=True)
    best = dict(rows_out[0]) if rows_out else {}

    doc: dict[str, Any] = {
        "schema": "aramaic_mvp_alert_threshold_sweep_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "source": {"audit_jsonl": str(audit_path)},
        "window": window_n,
        "rows_in_tail": len(tail),
        "rows": rows_out,
        "best": best,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
