#!/usr/bin/env python3
"""Materialize fixed byeongjeung/yakri proxy mapping table (Step 1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "sasang_byeongjeung_yakri_proxy_table_v1_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    payload = {
        "schema": "sasang_byeongjeung_yakri_proxy_table_v1",
        "generated_at_utc": _now_utc(),
        "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
        "source_script": "scripts/build_sasang_symptom_market_proxy_v1.py",
        "microstructure_layer": {
            "vix_spike_proxy": "0.55*volatility_rarefaction_proxy + 0.45*abs(heat_proxy-cold_proxy)",
            "volume_surge_proxy": "0.50*volatility_rarefaction_proxy + 0.40*heat_proxy + 0.10*(1-cold_proxy)",
            "spread_stress_proxy": "0.40*(1-volatility_rarefaction_proxy) + 0.60*abs(heat_proxy-cold_proxy)",
            "funding_extreme_proxy": "heat_proxy - cold_proxy (clipped -1..1)",
        },
        "symptom_layer": {
            "sweating": "0.60*vix_spike_proxy + 0.40*volume_surge_proxy",
            "dyspepsia": "0.65*spread_stress_proxy + 0.35*abs(funding_extreme_proxy)",
            "chills": "0.70*spread_stress_proxy + 0.30*max(0,-funding_extreme_proxy)",
            "thirst": "0.55*volume_surge_proxy + 0.45*vix_spike_proxy",
        },
        "stage_layer": {
            "severity": "0.35*sweating + 0.25*dyspepsia + 0.20*chills + 0.20*thirst",
            "stage_thresholds": {"early_lt": 0.48, "mid_lt": 0.68, "late_gte": 0.68},
        },
        "constraints": {
            "deterministic_price_prediction_forbidden": True,
            "research_only": True,
            "note": "This table is frozen for Step-1 proxy consistency; changes require explicit review.",
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
