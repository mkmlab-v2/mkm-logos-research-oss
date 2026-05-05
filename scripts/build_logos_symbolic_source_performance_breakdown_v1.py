#!/usr/bin/env python3
"""Build source_id-level performance breakdown for Logos symbolic backtest."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKTEST = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_source_performance_breakdown_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _hit_rate(hits: int, n: int) -> float | None:
    return round(hits / n, 6) if n else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    backtest = _load_json(Path(args.backtest_json).resolve())
    rows = backtest.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid backtest rows")

    by_source: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "hits": 0})
    by_source_split: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"n": 0, "hits": 0}))
    by_source_pred: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        if not isinstance(row, dict):
            continue
        source = str(row.get("source_id") or "unknown")
        split = str(row.get("dataset_partition") or "unspecified")
        pred = str(row.get("predicted_direction") or "unknown")
        hit = int(row.get("hit") or 0)
        by_source[source]["n"] += 1
        by_source[source]["hits"] += hit
        by_source_split[source][split]["n"] += 1
        by_source_split[source][split]["hits"] += hit
        by_source_pred[source][pred] += 1

    source_rows: list[dict[str, Any]] = []
    for source, stat in sorted(by_source.items(), key=lambda kv: kv[1]["n"], reverse=True):
        split_summary = {
            split: {
                "n_evaluated": s["n"],
                "hits": s["hits"],
                "hit_rate": _hit_rate(s["hits"], s["n"]),
            }
            for split, s in sorted(by_source_split[source].items())
        }
        source_rows.append(
            {
                "source_id": source,
                "n_evaluated": stat["n"],
                "hits": stat["hits"],
                "hit_rate": _hit_rate(stat["hits"], stat["n"]),
                "predicted_direction_counts": dict(sorted(by_source_pred[source].items())),
                "split_summary": split_summary,
            }
        )

    best = max(source_rows, key=lambda x: (x["hit_rate"] if isinstance(x["hit_rate"], float) else -1.0, x["n_evaluated"])) if source_rows else None
    worst = min(source_rows, key=lambda x: (x["hit_rate"] if isinstance(x["hit_rate"], float) else 2.0, -x["n_evaluated"])) if source_rows else None

    out = {
        "schema": "logos_symbolic_source_performance_breakdown_v1",
        "generated_at_utc": _now(),
        "backtest_json": str(Path(args.backtest_json).resolve()).replace("\\", "/"),
        "summary": {
            "n_sources": len(source_rows),
            "n_rows": len(rows),
            "best_source_id": best["source_id"] if best else None,
            "best_hit_rate": best["hit_rate"] if best else None,
            "worst_source_id": worst["source_id"] if worst else None,
            "worst_hit_rate": worst["hit_rate"] if worst else None,
        },
        "source_performance": source_rows,
    }

    out_path = Path(args.output_json).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

