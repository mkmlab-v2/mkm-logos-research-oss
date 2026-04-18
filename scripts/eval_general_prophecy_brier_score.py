#!/usr/bin/env python3
"""Mean Brier score for resolved binary questions in a general_prophecy registry."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_brier_eval_latest.json"
SCHEMA = "general_prophecy_brier_eval_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _last_forecast(forecasts: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not forecasts:
        return None
    sorted_f = sorted([f for f in forecasts if isinstance(f, dict)], key=lambda fc: str(fc.get("issued_at_utc") or ""))
    return sorted_f[-1] if sorted_f else None


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _median_int(vals: list[int]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    m = n // 2
    if n % 2 == 1:
        return float(s[m])
    return (s[m - 1] + s[m]) / 2.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing {ns.input}", file=sys.stderr)
        return 2
    doc = _load(ns.input)
    if doc.get("schema") != "general_prophecy_registry_v1":
        print("input must be general_prophecy_registry_v1", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    by_track: dict[str, list[float]] = defaultdict(list)
    by_domain_tag: dict[str, list[float]] = defaultdict(list)
    by_month: dict[str, list[float]] = defaultdict(list)
    by_resolved_month: dict[str, list[float]] = defaultdict(list)
    pending_count = 0
    overdue_count = 0
    pending_days_to_deadline: list[int] = []
    now_utc = datetime.now(timezone.utc)

    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        if (q.get("outcome_spec") or {}).get("kind") != "binary":
            continue
        res = q.get("resolution") or {}
        if res.get("status") == "pending":
            pending_count += 1
            ddl = q.get("resolution_deadline_utc")
            if isinstance(ddl, str):
                dt = _parse_utc(ddl)
                if dt is not None:
                    days = int((dt - now_utc).total_seconds() // 86400)
                    pending_days_to_deadline.append(days)
                    if dt < now_utc:
                        overdue_count += 1
        if res.get("status") != "resolved":
            continue
        ob = res.get("outcome_binary")
        if not isinstance(ob, bool):
            continue
        fc = _last_forecast([x for x in (q.get("forecasts") or []) if isinstance(x, dict)])
        if not fc or not isinstance(fc.get("probability_0_1"), (int, float)):
            continue
        issued_at = fc.get("issued_at_utc")
        p = float(fc["probability_0_1"])
        y = 1.0 if ob else 0.0
        b = (p - y) ** 2
        track = q.get("prophecy_track")
        if not isinstance(track, str) or not track.strip():
            track = "general"
        else:
            track = track.strip()
        by_track[track].append(b)
        tags = q.get("domain_tags")
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str) and t.strip():
                    by_domain_tag[t.strip()].append(b)
        if isinstance(issued_at, str) and len(issued_at) >= 7 and issued_at[4] == "-":
            by_month[issued_at[:7]].append(b)
        resolved_at = res.get("resolved_at_utc")
        if isinstance(resolved_at, str) and len(resolved_at) >= 7 and resolved_at[4] == "-":
            by_resolved_month[resolved_at[:7]].append(b)
        rows.append(
            {
                "question_id": q.get("question_id"),
                "prophecy_track": track,
                "domain_tags": [t for t in (tags or []) if isinstance(t, str)],
                "issued_at_utc": issued_at,
                "probability_0_1": p,
                "outcome_binary": ob,
                "brier_contribution": round(b, 6),
            }
        )

    n = len(rows)
    mean_brier = round(sum(r["brier_contribution"] for r in rows) / n, 6) if n else None
    track_order = ("general", "financial", "personalized")
    by_prophecy_track: dict[str, dict[str, Any]] = {}
    for t in track_order:
        vals = by_track.get(t) or []
        if vals:
            by_prophecy_track[t] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}
    for t, vals in sorted(by_track.items()):
        if t in track_order or not vals:
            continue
        by_prophecy_track[t] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}

    by_domain_tag_metrics: dict[str, dict[str, Any]] = {}
    for tag, vals in sorted(by_domain_tag.items()):
        if vals:
            by_domain_tag_metrics[tag] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}
    by_month_metrics: dict[str, dict[str, Any]] = {}
    for month, vals in sorted(by_month.items()):
        if vals:
            by_month_metrics[month] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}
    by_resolved_month_metrics: dict[str, dict[str, Any]] = {}
    for month, vals in sorted(by_resolved_month.items()):
        if vals:
            by_resolved_month_metrics[month] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}

    metrics: dict[str, Any] = {
        "mean_brier_score": mean_brier,
        "n_evaluated": n,
        "by_prophecy_track": by_prophecy_track,
        "by_domain_tag": by_domain_tag_metrics,
        "by_month": by_month_metrics,
        "by_resolved_month": by_resolved_month_metrics,
        "pending_count": pending_count,
        "overdue_count": overdue_count,
        "median_days_to_deadline": _median_int(pending_days_to_deadline),
    }
    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "inputs": {"registry_path": str(ns.input.resolve())},
        "metrics": metrics,
        "rows": rows,
        "note": "binary + resolved + last forecast only; void/categorical skipped; missing prophecy_track -> general",
    }
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(text, encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
