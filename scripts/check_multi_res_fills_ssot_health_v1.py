#!/usr/bin/env python3
"""SSOT drift guard: primary trades vs cache vs multi_res index ([HYPO]).

  py scripts/check_multi_res_fills_ssot_health_v1.py
  py scripts/check_multi_res_fills_ssot_health_v1.py --write-json
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/trades_treatment.json"
CACHE = ROOT / "reports/btrack_fills_daily_feature_cache_v1_latest.json"
INDEX = ROOT / "reports/multi_res_fills_index_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/multi_res_fills_ssot_health_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return len(raw)
    return 0


def build_health(*, allow_fallback: bool = False) -> dict[str, Any]:
    primary_rows = _load_rows(PRIMARY)
    cache_rows = 0
    cache_buckets = 0
    if CACHE.is_file():
        cache = json.loads(CACHE.read_text(encoding="utf-8-sig"))
        stats = cache.get("stats") or {}
        cache_rows = int(stats.get("n_fill_rows") or 0)
        cache_buckets = int(stats.get("n_daily_buckets") or 0)

    index_rows = 0
    index_buckets = 0
    fallback_used = None
    trades_source = None
    if INDEX.is_file():
        idx = json.loads(INDEX.read_text(encoding="utf-8-sig"))
        meta = idx.get("meta") or {}
        index_rows = int(meta.get("n_fill_rows") or 0)
        index_buckets = int(meta.get("n_daily_buckets") or 0)
        fallback_used = meta.get("fallback_used")
        trades_source = meta.get("trades_source")

    issues: list[str] = []
    if primary_rows <= 0:
        issues.append("primary_trades_empty")
    if fallback_used is True and not allow_fallback:
        issues.append("index_fallback_used")
    if primary_rows > 0 and cache_rows > 0 and primary_rows != cache_rows:
        issues.append(f"primary_cache_row_mismatch:{primary_rows}!={cache_rows}")
    if primary_rows > 0 and index_rows > 0 and primary_rows != index_rows:
        issues.append(f"primary_index_row_mismatch:{primary_rows}!={index_rows}")

    ok = len(issues) == 0
    return {
        "schema": "multi_res_fills_ssot_health_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "ok": ok,
        "issues": issues,
        "counts": {
            "primary_rows": primary_rows,
            "cache_rows": cache_rows,
            "cache_daily_buckets": cache_buckets,
            "index_rows": index_rows,
            "index_daily_buckets": index_buckets,
        },
        "index_meta": {
            "fallback_used": fallback_used,
            "trades_source": trades_source,
        },
        "paths": {
            "primary": str(PRIMARY.relative_to(ROOT)).replace("\\", "/"),
            "cache": str(CACHE.relative_to(ROOT)).replace("\\", "/"),
            "index": str(INDEX.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-json", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--allow-fallback", action="store_true")
    args = ap.parse_args()

    doc = build_health(allow_fallback=args.allow_fallback)
    if args.write_json:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"ok": doc["ok"], "issues": doc["issues"], "counts": doc["counts"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
