#!/usr/bin/env python3
"""Emit docs/final/artifacts/prophecy_health_status_latest.json (B-track prophecy observability).

Aggregates on-disk SSOT: market CSV freshness, last eval_prophecy_hit_rate mode, hypothesis provenance.
No network calls.
"""
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

from scripts.prophecy_hit_rate_ssot_v1 import DAILY_OPERATIONAL, HEADLINE_KPI  # noqa: E402

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_health_status_latest.json"
KOSPI_DEFAULT = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
BTC_DEFAULT = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
EVAL_DEFAULT = DAILY_OPERATIONAL
HEADLINE_EVAL = HEADLINE_KPI
HYP_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
P15_SHADOW_DEFAULT = ROOT / "reports/btrack_daily_p15_shadow_status_v1_latest.json"
SCHEMA_ID = "prophecy_health_status_v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _file_meta(path: Path) -> dict[str, Any]:
    try:
        rel = str(path.resolve().relative_to(ROOT))
    except ValueError:
        rel = str(path.resolve())
    out: dict[str, Any] = {"path": rel}
    if not path.is_file():
        out["exists"] = False
        return out
    st = path.stat()
    out["exists"] = True
    out["bytes"] = st.st_size
    out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    return out


def _csv_last_date_and_rows(path: Path) -> tuple[str | None, int | None]:
    if not path.is_file():
        return None, None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None, len(lines)
    last_date: str | None = None
    nrows = 0
    try:
        r = csv.DictReader(lines)
        fieldnames = r.fieldnames or []
        if "Date" not in fieldnames:
            return None, None
        for row in r:
            nrows += 1
            d = (row.get("Date") or "").strip()
            if d:
                last_date = d[:10]
    except csv.Error:
        return None, None
    return last_date, nrows


def _infer_hypothesis_route(doc: dict[str, Any]) -> str:
    prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
    model = str(prov.get("llm_model") or "").lower()
    if "gemini" in model:
        return "gemini"
    if "stub_heuristic" in model:
        return "stub_legacy"
    if "rule_based_ensemble" in model:
        return "ensemble_default"
    if model:
        return "other"
    return "unknown"


def _resolve_btc_path(env_btc: str | None) -> Path:
    if env_btc and Path(env_btc).is_file():
        return Path(env_btc).resolve()
    if BTC_DEFAULT.is_file():
        return BTC_DEFAULT.resolve()
    return BTC_DEFAULT


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_DEFAULT)
    args = ap.parse_args()

    env_btc = __import__("os").environ.get("MKM_BTC_DAILY_CSV", "").strip() or None
    btc_path = _resolve_btc_path(env_btc)

    k_meta = _file_meta(args.kospi_csv)
    k_last, k_n = _csv_last_date_and_rows(args.kospi_csv)
    k_meta["last_row_date"] = k_last
    k_meta["data_rows"] = k_n

    b_meta = _file_meta(btc_path)
    b_last, b_n = _csv_last_date_and_rows(btc_path)
    b_meta["last_row_date"] = b_last
    b_meta["data_rows"] = b_n

    eval_doc: dict[str, Any] = {}
    if EVAL_DEFAULT.is_file():
        try:
            eval_doc = json.loads(EVAL_DEFAULT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            eval_doc = {}

    run_mode = eval_doc.get("run_mode") if isinstance(eval_doc.get("run_mode"), str) else None
    eval_status = eval_doc.get("status")
    hit_path = "unknown"
    if run_mode in ("price", "proxy"):
        hit_path = run_mode
    elif not EVAL_DEFAULT.is_file():
        hit_path = "eval_missing"

    hyp_doc: dict[str, Any] = {}
    if HYP_DEFAULT.is_file():
        try:
            hyp_doc = json.loads(HYP_DEFAULT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            hyp_doc = {}

    route = _infer_hypothesis_route(hyp_doc)
    prov = hyp_doc.get("provenance") if isinstance(hyp_doc.get("provenance"), dict) else {}
    llm_model = prov.get("llm_model")

    p15_shadow: dict[str, Any] = {}
    if P15_SHADOW_DEFAULT.is_file():
        try:
            p15_shadow = json.loads(P15_SHADOW_DEFAULT.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            p15_shadow = {"load_error": True}

    warnings: list[str] = []
    if not k_meta.get("exists"):
        warnings.append("kospi_csv_missing_expect_proxy_or_skip_price_path")
    if hit_path == "proxy":
        warnings.append("hit_rate_eval_used_proxy_not_directional_price_metric")
    if hit_path == "eval_missing":
        warnings.append("prophecy_hit_rate_eval_latest_json_missing_run_eval_prophecy_hit_rate_v1")
    doc: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": "1.0.0",
        "generated_at_utc": _utc_now_iso(),
        "workspace_root": str(ROOT),
        "chain": {
            "primary_script": "scripts/run_btrack_daily_hypothesis_chain.ps1",
            "market_bootstrap": "scripts/fetch_kospi_yfinance_csv.py + scripts/fetch_btc_yfinance_csv.py when not -SkipMarketDataRefresh",
        },
        "market_csv": {
            "kospi": k_meta,
            "btc": b_meta,
            "btc_resolution_note": "Uses MKM_BTC_DAILY_CSV when set and file exists; else research/market_data/btc_daily_external_yf.csv",
        },
        "hit_rate_eval_pointer": str(EVAL_DEFAULT.relative_to(ROOT)),
        "hit_rate_eval_summary": {
            "run_mode": run_mode,
            "status": eval_status,
            "eval_generated_at_utc": eval_doc.get("generated_at_utc"),
            "operational_path": hit_path,
        },
        "btrack_hypothesis_pointer": str(HYP_DEFAULT.relative_to(ROOT)),
        "btrack_hypothesis_summary": {
            "llm_model": llm_model,
            "route_inferred": route,
        },
        "p15_abstain_shadow_pointer": str(P15_SHADOW_DEFAULT.relative_to(ROOT)),
        "p15_abstain_shadow_summary": {
            "operator_recommendation": (p15_shadow.get("daily_chain_hook") or {}).get(
                "operator_recommendation"
            ),
            "policy_posture_7d": p15_shadow.get("policy_posture_7d"),
            "window_trading_days": p15_shadow.get("window_trading_days"),
            "generated_at_utc": p15_shadow.get("generated_at_utc"),
        }
        if P15_SHADOW_DEFAULT.is_file()
        else None,
        "flags": {
            "proxy_mode_or_eval_missing": hit_path in ("proxy", "eval_missing"),
            "kospi_csv_present": bool(k_meta.get("exists")),
        },
        "documentation_notes": [
            "Yahoo Finance daily OHLCV is end-of-day; last_row_date may lag an intraday brokerage headline until the session prints a daily bar.",
        ],
        "warnings": warnings,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
