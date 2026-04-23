#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda x: float(x.get("score", 0.0)), reverse=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build canon-lane-only summary from original_corpus_regime_singularity_report_v1 JSON."
    )
    ap.add_argument(
        "--input-json",
        required=True,
        help="Path to singularity report JSON (canon-only or with-canon).",
    )
    ap.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Top N rows per regime and global canon list (default: 20).",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_lane_summary_v1.json",
    )
    args = ap.parse_args()

    data = _read_json(Path(args.input_json))
    top_n = int(args.top_n)

    canon_rows = [r for r in (data.get("top_global_singularities") or []) if r.get("lane") == "canon"]
    if not canon_rows:
        canon_rows = list(data.get("top_canon_singularities") or [])
    canon_rows = _sort_rows(canon_rows)

    by_regime: dict[str, list[dict[str, Any]]] = {}
    for row in canon_rows:
        regime = str(row.get("best_regime") or "unknown")
        by_regime.setdefault(regime, []).append(row)

    by_regime_top = {k: _sort_rows(v)[:top_n] for k, v in by_regime.items()}
    regime_counts = {k: len(v) for k, v in by_regime.items()}

    out = {
        "schema": "original_corpus_regime_singularity_canon_lane_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "input_json": str(args.input_json),
            "top_n": top_n,
        },
        "counts": {
            "canon_rows_in_source_top": len(canon_rows),
            "regime_counts": regime_counts,
        },
        "top_canon_global": canon_rows[:top_n],
        "top_canon_by_regime": by_regime_top,
        "note": "Readability helper for canon lane only; derived from singularity report top rows.",
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

