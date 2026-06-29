#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC multilens v2 blend backtest [HYPO][research_only].

Reuses June KOSPI multilens blend logic with BTC-USD closes for realized returns.
Session myeongni panel remains KRX-session calendar (09:00 Asia/Seoul); independent
lenses use latest artifact snapshots (same caveat as KOSPI backtest).
Does not modify June lane apply state or Track A gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json  # noqa: E402
from scripts.run_kospi_multilens_blend_backtest_v1 import (  # noqa: E402
    EVOLUTION_RULES,
    _load_closes,
    _load_panel,
    run_backtest,
)

BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_full_window_v1.csv"
DEFAULT_OUT = ROOT / "reports/btc_multilens_blend_backtest_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/btc_multilens_blend_backtest_latest.json"


def _patch_btc_schema(doc: dict[str, Any], *, btc_csv: Path) -> dict[str, Any]:
    doc = dict(doc)
    doc["schema"] = "btc_multilens_blend_backtest_v1"
    doc["instrument"] = "btc"
    doc["ohlcv_csv"] = str(btc_csv)
    doc["cross_asset_note_ko"] = (
        "KOSPI June lane v2_lens3_heavy 교차 검증용. 세션 명리는 KRX 캘린더, 수익률은 BTC-USD. "
        "June apply·Track A 자동 합선 금지."
    )
    w = doc.get("window")
    if isinstance(w, dict):
        w = dict(w)
        w["instrument"] = "btc"
        doc["window"] = w
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--btc-csv", type=Path, default=BTC_CSV)
    ap.add_argument("--date-from", default="2010-01-01")
    ap.add_argument("--date-to", default="2026-06-05")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.panel_csv.is_file():
        print(f"Missing panel: {args.panel_csv}", file=sys.stderr)
        return 2
    if not args.btc_csv.is_file():
        print(f"Missing BTC csv: {args.btc_csv}", file=sys.stderr)
        return 2

    rules = _read_json(EVOLUTION_RULES)
    panel = _load_panel(args.panel_csv)
    closes = _load_closes(args.btc_csv)
    doc = run_backtest(
        panel_by_date=panel,
        closes=closes,
        date_from=args.date_from,
        date_to=args.date_to,
        rules=rules,
        neutral_bps=float(rules.get("neutral_bps", 5.0)),
    )
    doc = _patch_btc_schema(doc, btc_csv=args.btc_csv)

    lens3 = next((r for r in doc.get("variants") or [] if r.get("variant_id") == "v2_lens3_heavy"), None)
    if lens3:
        doc["v2_lens3_heavy"] = lens3

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    best = doc.get("best_variant") or {}
    m = best.get("metrics") or {}
    l3m = (lens3 or {}).get("metrics") or {}
    print(
        f"WROTE: {args.output.resolve()} window={args.date_from}..{args.date_to} "
        f"n={doc['window']['n_calendar_days']} best={best.get('variant_id')} "
        f"soft={m.get('soft_hit_rate')} dir={m.get('directional_hit_rate')} "
        f"lens3_soft={l3m.get('soft_hit_rate')} lens3_dir={l3m.get('directional_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
