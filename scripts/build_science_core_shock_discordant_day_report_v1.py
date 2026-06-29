#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core shock-window discordant-day report [HYPO][research_only].

Per-date short_1d lens directions + outcomes for May–Jun 2026 shock study.
Includes macro_only diversity audit (sticky bear gate check).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _ensure_science_jsonl,
    build_daily_short_rows,
)

DEFAULT_OUT = ROOT / "reports/science_core_shock_discordant_day_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_shock_discordant_day_v1_latest.json"
DEFAULT_FROM = "2026-05-01"
DEFAULT_TO = "2026-06-08"
DEFAULT_SHOCK_BPS = 100.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _macro_diversity_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    macro_dirs = [str((r.get("predictions") or {}).get("macro_only") or "missing") for r in rows]
    counts = Counter(macro_dirs)
    n = len(rows)
    dominant = counts.most_common(1)[0] if counts else ("missing", 0)
    return {
        "n_days": n,
        "direction_counts": dict(counts),
        "dominant_direction": dominant[0],
        "dominant_share": round(dominant[1] / n, 4) if n else None,
        "sticky_regime_suspect": bool(n and dominant[1] / n >= 0.85 and dominant[0] in {"bear", "bull"}),
        "note_ko": "dominant_share>=0.85이면 macro_only 고 hit-rate는 sticky gate 의심.",
    }


def build_report(
    *,
    csv_path: Path,
    science_jsonl: Path,
    date_from: str,
    date_to: str,
    neutral_bps: float,
    shock_move_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    logos_jsonl: Path | None = None,
    myeongni_momentum_window: int,
) -> dict[str, Any]:
    daily = build_daily_short_rows(
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=myeongni_momentum_window,
    )
    shock_rows = [
        r
        for r in daily
        if r.get("forward_return_bps") is not None and abs(float(r["forward_return_bps"])) >= shock_move_bps
    ]
    discordant = [r for r in daily if r.get("discordant_science_vs_sasang") or r.get("discordant_science_vs_macro_only")]

    science_hits = sum(
        1 for r in daily if (r.get("outcomes_short_1d") or {}).get("science_core") == "HIT"
    )
    science_fails = sum(
        1 for r in daily if (r.get("outcomes_short_1d") or {}).get("science_core") == "FAIL"
    )
    combo_hits = sum(
        1 for r in daily if (r.get("outcomes_short_1d") or {}).get("science_plus_sasang") == "HIT"
    )
    combo_fails = sum(
        1 for r in daily if (r.get("outcomes_short_1d") or {}).get("science_plus_sasang") == "FAIL"
    )
    macro_hits = sum(
        1 for r in daily if (r.get("outcomes_short_1d") or {}).get("macro_only") == "HIT"
    )
    macro_fails = sum(
        1 for r in daily if (r.get("outcomes_short_1d") or {}).get("macro_only") == "FAIL"
    )

    def _soft(h: int, f: int, n: int) -> float | None:
        return round((h + 0.5 * max(0, n - h - f)) / n, 4) if n else None

    n = len(daily)
    macro_audit = _macro_diversity_audit(daily)

    focus_dates = sorted(
        {str(r.get("session_date")) for r in shock_rows},
        reverse=True,
    )

    return {
        "schema": "science_core_shock_discordant_day_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "window": {"from": date_from, "to": date_to},
        "shock_move_bps_threshold": shock_move_bps,
        "n_calendar_days": n,
        "n_shock_move_days": len(shock_rows),
        "n_discordant_days": len(discordant),
        "macro_only_diversity_audit": macro_audit,
        "short_1d_soft_rates": {
            "science_core": _soft(science_hits, science_fails, n),
            "science_plus_sasang": _soft(combo_hits, combo_fails, n),
            "macro_only": _soft(macro_hits, macro_fails, n),
        },
        "focus_dates_large_move": focus_dates,
        "daily_rows": daily,
        "shock_move_rows": shock_rows,
        "discordant_rows": discordant,
        "methodology_ko": (
            "shock/discordant 일별 short_1d 관측. macro sticky 의심은 diversity audit 참조. "
            "Track A·실매매 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", type=str, default=DEFAULT_FROM)
    ap.add_argument("--date-to", type=str, default=DEFAULT_TO)
    ap.add_argument("--shock-move-bps", type=float, default=DEFAULT_SHOCK_BPS)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--kospi-csv", type=Path, default=v1.KOSPI_CSV)
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--logos-jsonl", type=Path, default=None)
    ap.add_argument("--myeongni-momentum-window", type=int, default=5)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    if not args.kospi_csv.is_file():
        print(f"Missing KOSPI CSV: {args.kospi_csv}", file=sys.stderr)
        return 1

    if args.rebuild_science or not args.science_jsonl.is_file():
        _ensure_science_jsonl(
            instrument="kospi",
            csv_path=args.kospi_csv,
            out_path=args.science_jsonl,
            date_from=min(args.date_from, "2026-01-01"),
            date_to=args.date_to,
            apply_overnight=True,
        )

    doc = build_report(
        csv_path=args.kospi_csv,
        science_jsonl=args.science_jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        shock_move_bps=args.shock_move_bps,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        logos_lens=args.logos_lens,
        logos_jsonl=args.logos_jsonl,
        myeongni_momentum_window=args.myeongni_momentum_window,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    print(
        f"WROTE: {args.output.resolve()} n={doc.get('n_calendar_days')} "
        f"shock={doc.get('n_shock_move_days')} discordant={doc.get('n_discordant_days')} "
        f"macro_sticky={doc.get('macro_only_diversity_audit', {}).get('sticky_regime_suspect')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
