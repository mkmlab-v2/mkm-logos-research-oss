#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "trackb_quaternion_top_combo_ranking_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect(pattern: str) -> list[Path]:
    return sorted(ART.glob(pattern))


def main() -> int:
    ap = argparse.ArgumentParser(description="Rank Track B v6 round3 combos by measured score.")
    ap.add_argument("--glob", default="trackb_quaternion_generalization_v6_round3*.json")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    rows: list[dict[str, Any]] = []
    for p in _collect(args.glob):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        best = doc.get("best") or {}
        if "min_short_bucket_rate" not in best:
            continue
        curve = best.get("curve") or []
        failures = best.get("failures") or []
        rows.append(
            {
                "artifact": str(p.relative_to(ROOT)).replace("\\", "/"),
                "mode": doc.get("mode"),
                "min_short_bucket_rate": float(best.get("min_short_bucket_rate", 0.0)),
                "failure_count": len(failures),
                "weights": best.get("weights"),
                "stage1_top_k": doc.get("stage1_top_k"),
                "beam_size": doc.get("beam_size"),
                "block_size": doc.get("block_size"),
                "semantic_fallback": bool(doc.get("semantic_fallback", False)),
                "curve": curve,
            }
        )

    rows = sorted(rows, key=lambda r: (-r["min_short_bucket_rate"], r["failure_count"], r["artifact"]))
    out = {
        "schema": "trackb_quaternion_top_combo_ranking_v1",
        "generated_at_utc": _utc_now(),
        "ranking_metric": "best.min_short_bucket_rate",
        "tie_breaker": ["failure_count_asc", "artifact_name_asc"],
        "candidate_count": len(rows),
        "top_k_requested": args.top_k,
        "top": rows[: max(1, args.top_k)],
        "fact_safe_note": "Ranking is over existing v6 round3 artifacts only; not a full global search.",
    }
    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
