#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enrich session panel with session_direction_score + KOSPI/BTC daily returns (B-track [HYPO])."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import (  # noqa: E402
    _mapping_from_score,
    _score_from_session_pillars,
)

NEUTRAL_BPS = 5.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig")
    r = csv.DictReader(text.splitlines())
    h = list(r.fieldnames or [])
    return h, [{k: (v or "") for k, v in row.items()} for row in r]


def _load_close_by_date(path: Path, date_col: str = "Date", close_col: str = "Close") -> dict[str, float]:
    _, rows = _read_csv(path)
    out: dict[str, float] = {}
    for row in rows:
        dk = str(row.get(date_col, ""))[:10]
        if len(dk) != 10:
            continue
        try:
            out[dk] = float(row[close_col])
        except ValueError:
            continue
    return out


def _direction_from_return(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, required=True)
    ap.add_argument("--kospi-csv", type=Path, default=ROOT / "research/market_data/kospi_daily_external_yf.csv")
    ap.add_argument("--btc-csv", type=Path, default=ROOT / "research/market_data/btc_daily_external_yf.csv")
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--neutral-bps", type=float, default=NEUTRAL_BPS)
    args = ap.parse_args()

    _, panel = _read_csv(args.panel_csv)
    kospi = _load_close_by_date(args.kospi_csv)
    btc = _load_close_by_date(args.btc_csv)

    dates = sorted({str(r.get("session_local_date", ""))[:10] for r in panel if r.get("session_local_date")})
    prev_k: dict[str, float] = {}
    prev_b: dict[str, float] = {}
    for i, d in enumerate(dates):
        if i > 0:
            pd = dates[i - 1]
            if pd in kospi:
                prev_k[d] = kospi[pd]
            if pd in btc:
                prev_b[d] = btc[pd]

    enriched: list[dict[str, Any]] = []
    for r in panel:
        d = str(r.get("session_local_date", ""))[:10]
        pillars = {
            "year": r.get("year_pillar", ""),
            "month": r.get("month_pillar", ""),
            "day": r.get("day_pillar", ""),
            "hour": r.get("hour_pillar", ""),
        }
        sc = _score_from_session_pillars({k: str(v) for k, v in pillars.items()})
        mt = _mapping_from_score(sc, args.neutral_band)
        row: dict[str, Any] = dict(r)
        row["session_direction_score"] = round(sc, 6)
        row["session_mapping_target"] = mt
        kc = kospi.get(d)
        bc = btc.get(d)
        row["kospi_close"] = kc if kc is not None else ""
        row["btc_close"] = bc if bc is not None else ""
        kr = br = ""
        kdir = bdir = ""
        if kc is not None and d in prev_k and prev_k[d]:
            kr = (kc - prev_k[d]) / prev_k[d]
            kdir = _direction_from_return(kr, args.neutral_bps)
        if bc is not None and d in prev_b and prev_b[d]:
            br = (bc - prev_b[d]) / prev_b[d]
            bdir = _direction_from_return(br, args.neutral_bps)
        row["kospi_daily_return"] = round(kr, 8) if kr != "" else ""
        row["btc_daily_return"] = round(br, 8) if br != "" else ""
        row["kospi_actual_direction"] = kdir
        row["btc_actual_direction"] = bdir
        enriched.append(row)

    fieldnames: list[str] = []
    for row in enriched:
        for k in row:
            if k not in fieldnames:
                fieldnames.append(k)

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding="utf-8") as fp:
        w = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in enriched:
            w.writerow({k: row.get(k, "") for k in fieldnames})

    def _hit(inst: str) -> dict[str, Any]:
        hits = miss = skip = 0
        for row in enriched:
            pred = row.get("session_mapping_target")
            act = row.get(f"{inst}_actual_direction")
            if not act or row.get(f"{inst}_daily_return") == "":
                skip += 1
                continue
            if pred == "sideways" or act == "neutral":
                skip += 1
                continue
            if pred == act:
                hits += 1
            else:
                miss += 1
        n = hits + miss
        return {
            "hits": hits,
            "miss": miss,
            "skipped": skip,
            "n_directional": n,
            "hit_rate": round(hits / n, 6) if n else None,
        }

    summary = {
        "schema": "session_myeongni_dual_ohlcv_enrich_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "inputs": {
            "panel_csv": str(args.panel_csv.resolve()),
            "kospi_csv": str(args.kospi_csv.resolve()),
            "btc_csv": str(args.btc_csv.resolve()),
        },
        "params": {"neutral_band": args.neutral_band, "neutral_bps": args.neutral_bps},
        "n_panel_rows": len(enriched),
        "hit_rate_session_mapping": {
            "kospi": _hit("kospi"),
            "btc": _hit("btc"),
        },
        "note_ko": "session_mapping_target vs same-day close/prev_close direction. sideways/neutral 제외.",
        "out_csv": str(args.out_csv.resolve()),
    }
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["hit_rate_session_mapping"], ensure_ascii=False))
    print(f"WROTE {args.out_csv} {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
