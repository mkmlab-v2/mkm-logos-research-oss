#!/usr/bin/env python3
"""Mean Brier score for resolved binary questions in a general_prophecy registry.

Uses the last forecast snapshot in forecasts[] (by issued_at_utc order) vs
resolution.outcome_binary (True -> 1, False -> 0). Skips pending/void/categorical.
"""
from __future__ import annotations

import argparse
import json
import sys
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
    def key(fc: dict[str, Any]) -> str:
        return str(fc.get("issued_at_utc") or "")
    sorted_f = sorted([f for f in forecasts if isinstance(f, dict)], key=key)
    return sorted_f[-1] if sorted_f else None


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
    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        if (q.get("outcome_spec") or {}).get("kind") != "binary":
            continue
        res = q.get("resolution") or {}
        if res.get("status") != "resolved":
            continue
        ob = res.get("outcome_binary")
        if not isinstance(ob, bool):
            continue
        fc = _last_forecast([x for x in (q.get("forecasts") or []) if isinstance(x, dict)])
        if not fc or not isinstance(fc.get("probability_0_1"), (int, float)):
            continue
        p = float(fc["probability_0_1"])
        y = 1.0 if ob else 0.0
        b = (p - y) ** 2
        rows.append(
            {
                "question_id": q.get("question_id"),
                "probability_0_1": p,
                "outcome_binary": ob,
                "brier_contribution": round(b, 6),
            }
        )

    n = len(rows)
    mean_brier = round(sum(r["brier_contribution"] for r in rows) / n, 6) if n else None
    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "inputs": {"registry_path": str(ns.input.resolve())},
        "metrics": {"mean_brier_score": mean_brier, "n_evaluated": n},
        "rows": rows,
        "note": "binary + resolved + last forecast only; void/categorical skipped",
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
