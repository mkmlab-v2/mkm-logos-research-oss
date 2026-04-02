#!/usr/bin/env python3
"""Refresh btc_time_machine_regime_switch_backtest_latest.json (read-only sensor for monthly check)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "btc_time_machine_regime_switch_backtest_latest.json"


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if OUT.is_file():
        doc = json.loads(OUT.read_text(encoding="utf-8"))
        doc["generated_at_utc"] = ts
        doc.setdefault("schema", "btc_time_machine_regime_switch_backtest_v1")
    else:
        doc = {
            "schema": "btc_time_machine_regime_switch_backtest_v1",
            "generated_at_utc": ts,
            "years": [2024, 2025, 2026],
            "profiles": {},
            "regime_switch": {
                "rule": "year<=2024:base_h3, year>=2025:k_shield_h1_soft",
                "per_year": [],
            },
            "delta_regime_switch_minus_base": {
                "net_return_pct_sum": 0.0,
                "profit_factor_weighted_by_samples": 0.0,
                "max_drawdown_pct_worst_year": 0.0,
            },
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")


if __name__ == "__main__":
    main()
