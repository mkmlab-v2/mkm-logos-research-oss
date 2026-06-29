#!/usr/bin/env python3
"""Aggregate Logos path ledger feedback into contribution scores (B-track stub).

Scores are stored separately from ledger rows (EvoRAG stage-0 backprop stub).
Does not mutate graph artifacts or promote Track A.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_path_contribution_scores_v1_latest.json"
UP_DELTA = 1.0
DOWN_DELTA = -0.5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def aggregate_path_contribution_scores(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    paths: dict[str, dict[str, Any]] = {}
    for record in records:
        retrieval = record.get("retrieval") or {}
        feedback = record.get("feedback") or {}
        pid = str(retrieval.get("selected_path_id") or "").strip()
        if not pid:
            continue
        vote = str(feedback.get("vote") or "NONE")
        baseline = float(retrieval.get("path_score_baseline") or 100.0)
        ts = str(record.get("ts_utc") or "")

        if pid not in paths:
            paths[pid] = {
                "contribution_score": baseline,
                "up_votes": 0,
                "down_votes": 0,
                "none_votes": 0,
                "observations": 0,
                "last_updated_utc": ts,
            }

        row = paths[pid]
        row["observations"] += 1
        if vote == "UP":
            row["up_votes"] += 1
            row["contribution_score"] = round(float(row["contribution_score"]) + UP_DELTA, 4)
        elif vote == "DOWN":
            row["down_votes"] += 1
            row["contribution_score"] = round(float(row["contribution_score"]) + DOWN_DELTA, 4)
        else:
            row["none_votes"] += 1
        if ts and ts >= str(row.get("last_updated_utc") or ""):
            row["last_updated_utc"] = ts

    return paths


def build_contribution_scores_doc(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "logos_path_contribution_scores_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "policy": {
            "evolution_stage": "stub_aggregate_v1",
            "up_delta": UP_DELTA,
            "down_delta": DOWN_DELTA,
            "must_not": ["auto_graph_mutation", "track_a_promotion", "live_send"],
        },
        "ledger_rows_aggregated": len(records),
        "paths": aggregate_path_contribution_scores(records),
        "generator": "build_logos_path_contribution_scores_v1.py@1.0.0",
    }


def main(argv: list[str] | None = None) -> int:
    from scripts.logos_query_path_ledger_v1 import iter_ledger_records

    ap = argparse.ArgumentParser(description="Build logos_path_contribution_scores from path ledger JSONL")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    records = iter_ledger_records(ROOT)
    doc = build_contribution_scores_doc(records)

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "paths": len(doc["paths"])}, ensure_ascii=False))
        return 0

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out.relative_to(ROOT)).replace("\\", "/"),
                "paths": len(doc["paths"]),
                "ledger_rows": doc["ledger_rows_aggregated"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
