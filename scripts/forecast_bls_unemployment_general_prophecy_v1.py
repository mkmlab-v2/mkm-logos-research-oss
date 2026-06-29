#!/usr/bin/env python3
"""Issue a pre-release forecast for BLS May-2026 SA unemployment (general_prophecy B-rail).

Uses recent FRED UNRATE rows + simple macro tilt. Re-opens resolution to pending when
``--reopen-pending`` (drops provisional resolve for a clean score cycle).

research_only · no Track A / live trading.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
REGISTRY = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if ENV_PATH.is_file():
        load_dotenv(ENV_PATH, override=False)
DEFAULT_OUT = ROOT / "reports" / "bls_unemployment_forecast_v1_latest.json"
QID = "seed.macro.us_bls_unrate_gt_43_20260606"
THRESHOLD = 4.3
MAY_2026_OBS_DATE = "2026-05-01"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fred_unrate(api_key: str, *, limit: int = 8) -> list[dict[str, str]]:
    q = parse.urlencode(
        {
            "series_id": "UNRATE",
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{q}"
    with request.urlopen(request.Request(url=url, method="GET"), timeout=20) as resp:
        doc = json.loads(resp.read().decode("utf-8"))
    rows: list[dict[str, str]] = []
    for row in doc.get("observations") or []:
        if not isinstance(row, dict):
            continue
        d = str(row.get("date") or "")
        v = str(row.get("value") or "").strip()
        if v and v != ".":
            rows.append({"date": d, "value": v})
    return rows


def _rates(rows: list[dict[str, str]]) -> list[float]:
    out: list[float] = []
    for r in rows:
        try:
            out.append(float(r["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _estimate_p_true(rates: list[float]) -> tuple[float, dict[str, Any]]:
    """P(SA unrate strictly > 4.3%) — heuristic, not econometric model."""
    meta: dict[str, Any] = {"threshold": THRESHOLD, "method": "fred_recent_heuristic_v1"}
    if not rates:
        return 0.35, {**meta, "reason": "no_fred_rows_default"}

    latest = rates[0]
    meta["latest_pct"] = latest
    window = rates[:6]
    meta["window_pct"] = window
    above = sum(1 for x in window if x > THRESHOLD)
    share_above = above / len(window)
    # At 4.3, need uptick to 4.4+; anchor low prior then adjust from recent drift.
    p = 0.22
    if latest > THRESHOLD:
        p = 0.72
    elif latest >= THRESHOLD - 0.05:
        p = 0.28 + 0.35 * share_above
    else:
        p = 0.12 + 0.25 * share_above
    if len(window) >= 2 and window[0] > window[1]:
        p = min(0.85, p + 0.08)
        meta["momentum"] = "up"
    elif len(window) >= 2 and window[0] < window[1]:
        p = max(0.08, p - 0.08)
        meta["momentum"] = "down"
    else:
        meta["momentum"] = "flat"
    p = round(max(0.05, min(0.95, p)), 3)
    meta["share_strictly_above_threshold_in_window"] = round(share_above, 3)
    return p, meta


def _find_question(doc: dict[str, Any]) -> dict[str, Any] | None:
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and q.get("question_id") == QID:
            return q
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", type=Path, default=REGISTRY)
    ap.add_argument("-o", "--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--in-place", action="store_true", default=True)
    ap.add_argument("--no-in-place", action="store_false", dest="in_place")
    ap.add_argument(
        "--reopen-pending",
        action="store_true",
        default=True,
        help="Set resolution.status=pending before forecast (default on).",
    )
    ap.add_argument("--probability", type=float, default=None, help="Override model p(true).")
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()

    if not ns.input.is_file():
        print(f"missing registry: {ns.input}", file=sys.stderr)
        return 2

    doc = json.loads(ns.input.read_text(encoding="utf-8-sig"))
    q = _find_question(doc)
    if q is None:
        print(f"missing question_id: {QID}", file=sys.stderr)
        return 2

    _load_dotenv()
    fred_key = os.environ.get("FRED_API_KEY", "").strip()
    fred_rows: list[dict[str, str]] = []
    if fred_key:
        try:
            fred_rows = _fred_unrate(fred_key)
        except Exception as e:
            print(f"WARN: FRED fetch failed: {e}", file=sys.stderr)

    rates = _rates(fred_rows)
    p, model_meta = _estimate_p_true(rates)
    if ns.probability is not None:
        p = max(0.0, min(1.0, float(ns.probability)))
        model_meta["override"] = True

    now = _utc()
    if ns.reopen_pending:
        q["resolution"] = {"status": "pending"}

    fc = q.get("forecasts")
    if not isinstance(fc, list):
        fc = []
        q["forecasts"] = fc
    entry = {
        "issued_at_utc": now,
        "probability_0_1": p,
        "source_kind": "hybrid",
        "source_detail": (
            "forecast_bls_unemployment_general_prophecy_v1;"
            + json.dumps(model_meta, ensure_ascii=False, separators=(",", ":"))
        )[:500],
        "brier_ready": True,
    }
    fc.append(entry)
    doc["generated_at_utc"] = now

    try:
        from jsonschema import Draft202012Validator

        schema = json.loads((ROOT / "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(doc)
    except Exception as e:
        print(f"registry schema validation failed: {e}", file=sys.stderr)
        return 2

    report = {
        "schema": "bls_unemployment_forecast_v1",
        "generated_at_utc": now,
        "question_id": QID,
        "hypothesis_tier": "B",
        "research_only": True,
        "question_ko": "2026년 5월 BLS SA 실업률이 4.3%를 엄격히 초과하는가?",
        "probability_true": p,
        "probability_false": round(1.0 - p, 3),
        "predicted_outcome_hint": "true" if p >= 0.5 else "false",
        "resolution_status": (q.get("resolution") or {}).get("status"),
        "model_meta": model_meta,
        "next_steps": [
            "py scripts/probe_bls_unemployment_may2026_v1.py",
            "powershell -File scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1 -Outcome true|false",
            "py scripts/run_btrack_predictability_harness_v1.py",
        ],
    }

    if ns.in_place:
        ns.input.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    text = json.dumps(report, ensure_ascii=False, indent=2)
    if ns.stdout_only:
        sys.stdout.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
