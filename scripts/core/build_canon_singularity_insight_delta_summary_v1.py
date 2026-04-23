#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _index_insights(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("row_id")): r for r in rows if r.get("row_id")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build delta summary from canon insight history.")
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_history_v1.jsonl",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_delta_summary_v1.json",
    )
    args = ap.parse_args()

    hist = _read_jsonl(Path(args.history_jsonl))
    latest = hist[-1] if hist else {}
    prev = hist[-2] if len(hist) >= 2 else {}

    latest_rows = list((latest or {}).get("insights") or [])
    prev_rows = list((prev or {}).get("insights") or [])
    li = _index_insights(latest_rows)
    pi = _index_insights(prev_rows)

    latest_ids = set(li.keys())
    prev_ids = set(pi.keys())
    added_ids = sorted(latest_ids - prev_ids)
    removed_ids = sorted(prev_ids - latest_ids)
    common_ids = sorted(latest_ids & prev_ids)

    changed: list[dict[str, Any]] = []
    for rid in common_ids:
        a = li[rid]
        b = pi[rid]
        if (
            str(a.get("best_regime")) != str(b.get("best_regime"))
            or float(a.get("score", 0.0)) != float(b.get("score", 0.0))
            or float(a.get("margin_vs_second", 0.0)) != float(b.get("margin_vs_second", 0.0))
        ):
            changed.append(
                {
                    "row_id": rid,
                    "prev_best_regime": b.get("best_regime"),
                    "latest_best_regime": a.get("best_regime"),
                    "prev_score": float(b.get("score", 0.0)),
                    "latest_score": float(a.get("score", 0.0)),
                    "score_delta": round(float(a.get("score", 0.0)) - float(b.get("score", 0.0)), 8),
                }
            )

    out = {
        "schema": "original_corpus_regime_singularity_canon_insight_delta_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"history_jsonl": str(args.history_jsonl)},
        "counts": {
            "history_events_total": len(hist),
            "latest_rows": len(latest_rows),
            "prev_rows": len(prev_rows),
            "added_count": len(added_ids),
            "removed_count": len(removed_ids),
            "changed_count": len(changed),
        },
        "latest_generated_at_utc": (latest or {}).get("generated_at_utc"),
        "prev_generated_at_utc": (prev or {}).get("generated_at_utc"),
        "added": [li[r] for r in added_ids],
        "removed": [pi[r] for r in removed_ids],
        "changed": changed,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

