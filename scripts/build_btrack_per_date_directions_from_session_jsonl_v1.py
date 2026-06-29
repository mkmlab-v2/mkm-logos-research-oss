#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build btrack_ensemble_per_date_directions_v1 JSON from session myeongni JSONL (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mapping_to_predicted(mt: str) -> str:
    m = str(mt or "").strip().lower()
    if m == "bull":
        return "bull"
    if m == "bear":
        return "bear"
    if m in ("sideways", "neutral"):
        return "neutral"
    return "neutral"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        o = json.loads(raw)
        if isinstance(o, dict):
            lines.append(o)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--session-jsonl",
        type=Path,
        default=ROOT / "data/myeongni/myeongni_session_30d_v1.jsonl",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports/btrack_per_date_directions_session_myeongni_30d_v1.json",
    )
    ap.add_argument("--instrument", type=str, default="multi", help="Label for rows (multi|btc|kospi).")
    args = ap.parse_args()
    if not args.session_jsonl.is_file():
        print(f"missing {args.session_jsonl}", file=sys.stderr)
        return 2

    rows_out: list[dict[str, Any]] = []
    for line in _load_jsonl(args.session_jsonl):
        ed = str(line.get("eval_date") or line.get("session_local_date") or "")[:10]
        if len(ed) != 10:
            continue
        mt = line.get("mapping_target") or "sideways"
        sc = line.get("session_direction_score")
        pred = _mapping_to_predicted(str(mt))
        rows_out.append(
            {
                "eval_date": ed,
                "instrument": args.instrument,
                "predicted_direction": pred,
                "confidence": round(abs(float(sc)), 6) if sc is not None else 0.5,
                "ensemble_mode": "session_myeongni_v1",
                "session_direction_score": sc,
                "mapping_target": mt,
                "pillars_session": line.get("pillars_session"),
                "source": "manseryeok_session_v1",
            }
        )

    rows_out.sort(key=lambda r: r["eval_date"])
    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": _utc_now(),
        "ensemble_mode": "session_myeongni_v1",
        "research_only": True,
        "inputs": {"session_jsonl": str(args.session_jsonl.resolve())},
        "note": "Per-date directions from 09:00 KST session 四柱 only. Use with build_btrack_prophecy_score_from_ohlcv.py --per-date-direction-json.",
        "rows": rows_out,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE n_rows={len(rows_out)} path={args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
