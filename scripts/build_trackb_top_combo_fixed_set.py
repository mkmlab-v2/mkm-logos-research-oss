#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_RANKING = ART / "trackb_quaternion_top_combo_ranking_latest.json"
DEFAULT_OUT = ART / "trackb_quaternion_top_combo_fixed_set_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build fixed candidate set from Track B top combo ranking.")
    ap.add_argument("--ranking", default=str(DEFAULT_RANKING))
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument("--max-failures", type=int, default=0)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    ranking_path = Path(args.ranking) if Path(args.ranking).is_absolute() else (ROOT / args.ranking)
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    rows = ranking.get("top") or ranking.get("top10") or []

    selected: list[dict[str, Any]] = []
    for row in rows:
        if int(row.get("failure_count", 999999)) > args.max_failures:
            continue
        selected.append(
            {
                "artifact": row.get("artifact"),
                "score_min_short_bucket_rate": row.get("min_short_bucket_rate"),
                "failure_count": row.get("failure_count"),
                "weights": row.get("weights"),
                "stage1_top_k": row.get("stage1_top_k"),
                "beam_size": row.get("beam_size"),
                "block_size": row.get("block_size"),
                "semantic_fallback": row.get("semantic_fallback"),
            }
        )
        if len(selected) >= max(1, args.top_n):
            break

    out = {
        "schema": "trackb_quaternion_top_combo_fixed_set_v1",
        "generated_at_utc": _utc_now(),
        "source_ranking": str(ranking_path.resolve()).replace("\\", "/"),
        "selection_policy": {
            "top_n": args.top_n,
            "max_failures": args.max_failures,
            "ranking_metric": ranking.get("ranking_metric", "best.min_short_bucket_rate"),
            "tie_breaker": ranking.get("tie_breaker", ["failure_count_asc", "artifact_name_asc"]),
        },
        "selected_count": len(selected),
        "selected": selected,
        "fact_safe_note": "Fixed set is curated from prior measured artifacts; re-validate before promotion.",
        "out_of_scope": "No production promotion, no trading trigger.",
    }
    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
