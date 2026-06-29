#!/usr/bin/env python3
"""[HYPO] Audit KOSPI/BTC prediction pairing: operational dual vs dual-leg 180d score.

Explains why decouple-only spikes (P3) do not fire on canonical holdout7 / 180d panels.
research_only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OP_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_SCORE_180 = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_dual_leg_decouple_coverage_audit_v1_latest.json"
SCHEMA = "btrack_dual_leg_decouple_coverage_audit_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pair_stats(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        return {"label": label, "path": str(path), "missing": True}
    rows = [r for r in (_load(path).get("rows") or []) if isinstance(r, dict)]
    by: dict[str, dict[str, str]] = {}
    for r in rows:
        ed = str(r.get("eval_date"))[:10]
        inst = str(r.get("instrument") or "").lower()
        by.setdefault(ed, {})[inst] = str(r.get("predicted_direction") or "").lower()
    pairs: Counter[tuple[str, str]] = Counter()
    decouple_dates: list[str] = []
    for ed, o in sorted(by.items()):
        k = o.get("kospi", "")
        b = o.get("btc", "")
        if not k or not b:
            continue
        pairs[(k, b)] += 1
        if k == "bull" and b == "bear":
            decouple_dates.append(ed)
    synced = pairs.get(("neutral", "neutral"), 0) + pairs.get(("bull", "bull"), 0) + pairs.get(("bear", "bear"), 0)
    total = sum(pairs.values())
    return {
        "label": label,
        "path": str(path),
        "n_calendar_days": total,
        "pair_counts": {f"kospi_{k}_btc_{b}": c for (k, b), c in pairs.most_common()},
        "n_decouple_kospi_bull_btc_bear": len(decouple_dates),
        "decouple_dates_sample": decouple_dates[:12],
        "n_fully_synced_direction_pairs": synced,
        "pct_fully_synced": round(synced / total, 6) if total else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--operational-dual-json", type=Path, default=DEFAULT_OP_DUAL)
    ap.add_argument("--dual-180-score-json", type=Path, default=DEFAULT_SCORE_180)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    op = _pair_stats(args.operational_dual_json, "operational_15d_dual")
    d180 = _pair_stats(args.dual_180_score_json, "dual_leg_180d_score")

    op_dec = int(op.get("n_decouple_kospi_bull_btc_bear", 0) or 0)
    d180_dec = int(d180.get("n_decouple_kospi_bull_btc_bear", 0) or 0)
    d180_sync = d180.get("pct_fully_synced")

    root_cause = (
        f"operational dual decouple={op_dec}, dual_leg_180d decouple={d180_dec} — "
        "pairing alignment is not a blocker."
    )
    if d180_dec == 0 and op_dec > 0:
        root_cause = (
            f"operational dual has {op_dec} decouple days but "
            f"dual_leg_180d has 0 — rebuild 180d via separate KOSPI/BTC per-date ensemble, not mirrored legs."
        )
    elif isinstance(d180_sync, float) and d180_sync >= 0.999:
        root_cause = (
            "dual_leg_180d_score is effectively 100% synced (kospi,btc) direction pairs — "
            "decouple spikes cannot fire on that artifact."
        )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panels": [op, d180],
        "root_cause_ko": root_cause,
        "recommended_next_scripts": [
            "scripts/build_btrack_dual_per_date_directions_v1.py --recent-trading-days 180",
            "scripts/build_btrack_prophecy_score_from_ohlcv.py --force-dual-leg-panel --recent-trading-days 30",
            "scripts/build_btrack_btc_direction_error_spike_v1.py",
        ],
        "promotion_recommendation": "hold_research_only",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(root_cause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
