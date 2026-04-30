#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    out: dict[str, str] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        d = str(r.get("eval_date") or "")[:10]
        p = str(r.get("predicted_direction") or "").lower()
        if d and p in ("bull", "bear", "neutral"):
            out[d] = p
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge two BTC per-date prediction sources.")
    ap.add_argument("--source-a", type=Path, required=True)
    ap.add_argument("--source-b", type=Path, required=True)
    ap.add_argument("--weight-a", type=float, default=1.0)
    ap.add_argument("--weight-b", type=float, default=1.0)
    ap.add_argument("--tie-break", choices=("a", "neutral"), default="a")
    ap.add_argument("--output", type=Path, default=ART / "btc_per_date_direction_ensemble_merge_latest.json")
    args = ap.parse_args()

    a = _load(args.source_a if args.source_a.is_absolute() else (ROOT / args.source_a))
    b = _load(args.source_b if args.source_b.is_absolute() else (ROOT / args.source_b))
    dates = sorted(set(a.keys()) & set(b.keys()))

    rows: list[dict[str, Any]] = []
    for d in dates:
        va = a[d]
        vb = b[d]
        score = {"bull": 0.0, "bear": 0.0, "neutral": 0.0}
        score[va] += float(args.weight_a)
        score[vb] += float(args.weight_b)
        mx = max(score.values())
        winners = [k for k, v in score.items() if v == mx]
        if len(winners) == 1:
            pred = winners[0]
        else:
            pred = va if args.tie_break == "a" else "neutral"
        rows.append({"eval_date": d, "predicted_direction": pred})

    payload = {
        "schema": "btc_per_date_direction_ensemble_merge_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "source_a": str(args.source_a),
            "source_b": str(args.source_b),
            "weight_a": float(args.weight_a),
            "weight_b": float(args.weight_b),
            "tie_break": args.tie_break,
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} n_rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

