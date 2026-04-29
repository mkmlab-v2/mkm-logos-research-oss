#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _corr(xs: List[float], ys: List[float]) -> float:
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    mx = _mean(xs)
    my = _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0.0 or dy == 0.0:
        return 0.0
    return num / (dx * dy)


def _eval(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    usable = []
    for e in rows:
        emo = e.get("emotion") if isinstance(e.get("emotion"), dict) else {}
        labels = e.get("labels") if isinstance(e.get("labels"), dict) else {}
        v = emo.get("valence")
        pnl = labels.get("forward_pnl_1d")
        if isinstance(v, (int, float)) and isinstance(pnl, (int, float)):
            usable.append((float(v), float(pnl)))
    if not rows:
        return {"n_total": 0, "n_usable": 0, "coverage_ratio": 0.0, "corr_valence_vs_forward_pnl_1d": 0.0}
    cov = len(usable) / len(rows)
    return {
        "n_total": len(rows),
        "n_usable": len(usable),
        "coverage_ratio": cov,
        "corr_valence_vs_forward_pnl_1d": _corr([x[0] for x in usable], [x[1] for x in usable]),
        "mean_forward_pnl_1d": _mean([x[1] for x in usable]) if usable else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build source-sliced emotion evaluation report.")
    ap.add_argument("--events-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    args = ap.parse_args()

    events = list(_iter_jsonl(args.events_jsonl))
    kpi = [e for e in events if str(e.get("source")) == "kpi_derived_sentiment_proxy_v1"]
    atproto = [e for e in events if str(e.get("source")) == "atproto_operational_heuristic_v1"]
    kpi_atproto = [
        e
        for e in events
        if str(e.get("source")) in {"kpi_derived_sentiment_proxy_v1", "atproto_operational_heuristic_v1"}
    ]

    out = {
        "schema_version": "emotion_source_slice_report_v1",
        "slices": {
            "kpi_only": _eval(kpi),
            "atproto_only": _eval(atproto),
            "kpi_plus_atproto": _eval(kpi_atproto),
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
