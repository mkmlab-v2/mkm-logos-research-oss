#!/usr/bin/env python3
"""Build Top10 rank/score diff from compact FACTS Kaggle summary.

Reads current `facts_kaggle_top10_summary_latest.json`, appends snapshot history JSONL,
and writes a diff artifact against the immediately previous snapshot.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if isinstance(obj, dict):
                out.append(obj)
    return out


def _to_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    m: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = (
            str(r.get("model_proxy_slug") or "").strip().lower()
            or str(r.get("display_name") or "").strip().lower()
        )
        if key:
            m[key] = r
    return m


def _diff(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev_map = _to_map(previous)
    curr_map = _to_map(current)
    rows: list[dict[str, Any]] = []
    for key, cur in curr_map.items():
        prev = prev_map.get(key)
        cur_rank = cur.get("rank")
        cur_score = cur.get("average_score")
        prev_rank = prev.get("rank") if prev else None
        prev_score = prev.get("average_score") if prev else None
        rank_delta = None
        score_delta = None
        try:
            if cur_rank is not None and prev_rank is not None:
                rank_delta = int(prev_rank) - int(cur_rank)  # + means improved rank
        except Exception:
            rank_delta = None
        try:
            if cur_score is not None and prev_score is not None:
                score_delta = float(cur_score) - float(prev_score)
        except Exception:
            score_delta = None
        rows.append(
            {
                "display_name": cur.get("display_name"),
                "model_proxy_slug": cur.get("model_proxy_slug"),
                "rank_prev": prev_rank,
                "rank_curr": cur_rank,
                "rank_delta": rank_delta,
                "average_score_prev": prev_score,
                "average_score_curr": cur_score,
                "average_score_delta": score_delta,
                "status": "new" if prev is None else "existing",
            }
        )

    # models dropped from top-N
    for key, prev in prev_map.items():
        if key not in curr_map:
            rows.append(
                {
                    "display_name": prev.get("display_name"),
                    "model_proxy_slug": prev.get("model_proxy_slug"),
                    "rank_prev": prev.get("rank"),
                    "rank_curr": None,
                    "rank_delta": None,
                    "average_score_prev": prev.get("average_score"),
                    "average_score_curr": None,
                    "average_score_delta": None,
                    "status": "dropped",
                }
            )
    rows.sort(key=lambda x: (x.get("rank_curr") is None, x.get("rank_curr") or 9999))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build FACTS Kaggle top10 diff artifact.")
    ap.add_argument(
        "--summary-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_kaggle_top10_summary_latest.json"),
    )
    ap.add_argument(
        "--history-jsonl",
        type=Path,
        default=Path("docs/final/artifacts/facts_kaggle_top10_history_v1.jsonl"),
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_kaggle_top10_diff_latest.json"),
    )
    args = ap.parse_args()

    current = _load_json(args.summary_json)
    current_rows = current.get("kaggle_top_models_compact") or []
    history = _read_jsonl(args.history_jsonl)
    previous_entry = history[-1] if history else None
    previous_rows = (previous_entry or {}).get("kaggle_top_models_compact") or []

    diff_rows = _diff(current_rows, previous_rows)

    out = {
        "schema": "facts_kaggle_top10_diff_v1",
        "generated_at_utc": _now_utc_iso(),
        "source_summary": str(args.summary_json),
        "has_previous_snapshot": previous_entry is not None,
        "previous_generated_at_utc": (previous_entry or {}).get("generated_at_utc"),
        "matched_model": current.get("matched_model"),
        "internal_metrics": current.get("internal_metrics"),
        "diff_rows": diff_rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # Append new history entry after diff generation
    args.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.history_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(current, ensure_ascii=False) + "\n")

    print(f"[OK] wrote: {args.out_json}")
    print(f"[OK] history append: {args.history_jsonl}")
    print(f"[SUMMARY] prev_exists={previous_entry is not None}, rows={len(diff_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
