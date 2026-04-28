#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Estimate symbol-level walk-forward survivability.")
    ap.add_argument("--multi-symbol-json", default="docs/final/artifacts/multi_symbol_resonance_4d_latest.json")
    ap.add_argument("--selector-json", default="docs/final/artifacts/multi_symbol_candidate_selector_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_walkforward_survivability_latest.json")
    args = ap.parse_args()

    mp = resolve(args.multi_symbol_json)
    sp = resolve(args.selector_json)
    op = resolve(args.output_json)
    for p in (mp, sp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    multi = load(mp)
    selector = load(sp)
    selected = selector.get("selected") if isinstance(selector.get("selected"), list) else []
    selected_symbols = {str(x.get("seed_symbol")) for x in selected if isinstance(x, dict)}
    rows = multi.get("symbols") if isinstance(multi.get("symbols"), list) else []

    metrics: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("seed_symbol", "unknown"))
        coupling = float(row.get("coupling_strength", 0.0) or 0.0)
        resonance = float(row.get("resonance_score", 0.0) or 0.0)
        seq_len = int(row.get("sequence_length", 0) or 0)
        is_selected = symbol in selected_symbols

        # Proxy walk-forward signals (research lane): higher coupling/resonance helps;
        # longer sequence mildly increases overfit risk if unsupported.
        oos_survival_rate = clamp01(0.55 * coupling + 0.35 * resonance + 0.10 * (1.0 if is_selected else 0.0))
        false_positive_cost_proxy = clamp01((0.40 * (1.0 - coupling)) + (0.20 * (seq_len / 10.0)))
        survivability_score = clamp01((0.65 * oos_survival_rate) + (0.35 * (1.0 - false_positive_cost_proxy)))

        metrics.append(
            {
                "seed_symbol": symbol,
                "is_selected": is_selected,
                "sequence_length": seq_len,
                "coupling_strength": round(coupling, 6),
                "resonance_score": round(resonance, 6),
                "oos_survival_rate_proxy": round(oos_survival_rate, 6),
                "false_positive_cost_proxy": round(false_positive_cost_proxy, 6),
                "survivability_score": round(survivability_score, 6),
            }
        )

    ranked = sorted(metrics, key=lambda x: float(x.get("survivability_score", 0.0)), reverse=True)
    top_symbol = ranked[0]["seed_symbol"] if ranked else None
    out = {
        "schema": "multi_symbol_walkforward_survivability_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "metrics": ranked,
        "summary": {
            "symbol_count": len(ranked),
            "top_symbol_by_survivability": top_symbol,
            "mean_survivability_score": round(
                clamp01(sum(float(r.get("survivability_score", 0.0)) for r in ranked) / max(len(ranked), 1)),
                6,
            ),
        },
        "sources": {"multi_symbol_json": str(mp), "selector_json": str(sp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

