#!/usr/bin/env python3
"""Build concise SITREP text from latest war-prolongation artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    bundle = _load(ART / "war_prolongation_benchmark_bundle_20260406.json")
    health = _load(ART / "war_prolongation_benchmark_health_latest.json")
    promo = _load(ART / "war_prolongation_promotion_ready_latest.json")

    snap = bundle.get("snapshot", {})
    issues = health.get("issues", [])
    reasons = snap.get("gate_reasons", [])

    lines = [
        f"timestamp_utc={_now()}",
        "report=war_prolongation_sitrep_v1",
        f"cycle_status={'ok' if health.get('status') == 'ok' else 'attention'}",
        f"gate_decision={snap.get('gate_decision', 'UNKNOWN')}",
        f"promotion_ready={promo.get('promotion_ready', False)}",
        f"spot_hit_rate={snap.get('spot_hit_rate')}",
        f"window_h1={snap.get('window_hit_rate_h1')}",
        f"window_h5={snap.get('window_hit_rate_h5')}",
        f"window_h20={snap.get('window_hit_rate_h20')}",
        f"perf_per_w_uplift_pct={snap.get('perf_per_w_uplift_pct')}",
        f"health_issues={','.join(issues) if issues else 'none'}",
        f"gate_reasons={','.join(reasons) if reasons else 'none'}",
        "lane=btrack_observation_only",
    ]

    out_txt = ART / "war_prolongation_sitrep_latest.txt"
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {out_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

