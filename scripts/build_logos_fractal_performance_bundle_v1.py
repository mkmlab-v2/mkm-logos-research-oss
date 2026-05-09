#!/usr/bin/env python3
"""Join fractal resonance outputs with backtest metrics per split/tag."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "logos_fractal_performance_bundle_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _corr(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = sum((x - mx) ** 2 for x in xs) ** 0.5
    deny = sum((y - my) ** 2 for y in ys) ** 0.5
    if denx == 0.0 or deny == 0.0:
        return None
    return round(num / (denx * deny), 6)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build fractal-vs-performance bundle.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tags = [
        "latest",
        "contrastive_challenge",
        "contrastive_expanded",
        "split1",
        "split2",
        "split3",
        "blind_split",
        "blind_split_hardset",
    ]

    rows: list[dict[str, Any]] = []
    x_res: list[float] = []
    y_hr: list[float] = []

    for t in tags:
        frac = ART / f"logos_fractal_sign_reading_{t}_latest.json"
        bt = ART / f"logos_symbolic_event_backtest_{t}_latest.json"
        if t == "latest":
            frac = ART / "logos_fractal_sign_reading_latest_latest.json"
            bt = ART / "logos_symbolic_event_backtest_latest_latest.json"
        if not frac.exists() or not bt.exists():
            continue
        fdoc = _load_json(frac)
        bdoc = _load_json(bt)
        top = fdoc.get("top_match") or {}
        summ = bdoc.get("summary") or {}
        hr = float(summ.get("hit_rate") or 0.0)
        ns = summ.get("non_synthetic_hit_rate")
        ns_hr = float(ns) if ns is not None else None
        res = float(top.get("resonance_cosine") or 0.0)
        row = {
            "tag": t,
            "fractal_top_archetype": top.get("archetype_id"),
            "fractal_resonance_cosine": res,
            "fractal_signal": (fdoc.get("decision") or {}).get("signal"),
            "n_evaluated": int(summ.get("n_evaluated") or 0),
            "hit_rate": hr,
            "non_synthetic_n_evaluated": int(summ.get("non_synthetic_n_evaluated") or 0),
            "non_synthetic_hit_rate": ns_hr,
        }
        rows.append(row)
        x_res.append(res)
        y_hr.append(hr)
    out = {
        "schema": "logos_fractal_performance_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "rows": rows,
        "summary": {
            "run_count": len(rows),
            "corr_resonance_vs_hit_rate": _corr(x_res, y_hr),
            "corr_resonance_vs_non_synthetic_hit_rate": _corr(
                [r["fractal_resonance_cosine"] for r in rows if r["non_synthetic_hit_rate"] is not None],
                [float(r["non_synthetic_hit_rate"]) for r in rows if r["non_synthetic_hit_rate"] is not None],
            ),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "run_count": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

