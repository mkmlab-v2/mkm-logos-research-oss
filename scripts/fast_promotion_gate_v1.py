# @MKM12-METADATA
# Type: Logic
# Purpose: B-track fast promotion gate (shadow vs live candidate from score + hit rate + gates + external status)
#!/usr/bin/env python3
"""Combine promotion gates, hit-rate eval, external-feed status, and score rows into one gate JSON.

Writes ``docs/final/artifacts/fast_promotion_gate_v1_latest.json`` (schema ``fast_promotion_gate_v1``).
Research-only; does not route live trading.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMOTION = ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
DEFAULT_HIT_RATE = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_EXTERNAL_STATUS = ROOT / "docs/final/artifacts/external_feed_drop_validation_status_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/fast_promotion_gate_v1_latest.json"
SCHEMA = "fast_promotion_gate_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _promotion_combined_passed(doc: dict[str, Any] | None) -> bool:
    if not doc:
        return False
    if "combined_all_passed" in doc:
        return bool(doc.get("combined_all_passed"))
    return bool(doc.get("all_gates_passed"))


def _hit_metrics(hit_doc: dict[str, Any] | None) -> tuple[float, int]:
    if not hit_doc:
        return 0.0, 0
    m = hit_doc.get("metrics") if isinstance(hit_doc.get("metrics"), dict) else {}
    try:
        rate = float(m.get("price_directional_hit_rate", 0.0))
    except (TypeError, ValueError):
        rate = 0.0
    try:
        n = int(m.get("n_evaluated", 0))
    except (TypeError, ValueError):
        n = 0
    return rate, n


def _external_checks(
    ext: dict[str, Any] | None,
    *,
    allow_missing: bool,
    allow_degraded_live: bool,
) -> tuple[str, bool]:
    """Return (external_mode, external_live_ok)."""
    if not ext:
        mode = "missing"
        live_ok = bool(allow_missing)
        return mode, live_ok
    mode = str(ext.get("mode") or ext.get("latest_mode") or "unknown")
    degraded = bool(ext.get("degraded"))
    if degraded and not allow_degraded_live:
        return mode, False
    return mode, True


def main() -> int:
    ap = argparse.ArgumentParser(description="Fast promotion gate v1 (B-track measurement-only).")
    ap.add_argument("--promotion-gates", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--hit-rate", type=Path, default=DEFAULT_HIT_RATE)
    ap.add_argument("--external-status", type=Path, default=DEFAULT_EXTERNAL_STATUS)
    ap.add_argument("--score", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-hit-rate", type=float, default=0.5)
    ap.add_argument("--min-n", type=int, default=5)
    ap.add_argument(
        "--allow-external-degraded-for-live",
        action="store_true",
        help="Treat degraded external validation as live-OK (default: false).",
    )
    ap.add_argument(
        "--allow-missing-external-status",
        action="store_true",
        help="If external status JSON is absent, allow live_ok (default: false).",
    )
    args = ap.parse_args()

    pg = _load_json(args.promotion_gates)
    hr = _load_json(args.hit_rate)
    ext = _load_json(args.external_status)
    score = _load_json(args.score)

    rows = score.get("rows") if isinstance(score, dict) else None
    shadow_has_score_rows = bool(isinstance(rows, list) and len(rows) > 0)

    promotion_ok = _promotion_combined_passed(pg)
    rate, n_ev = _hit_metrics(hr)
    min_r = float(args.min_hit_rate)
    min_n = int(args.min_n)
    hit_rate_ok = rate >= min_r and n_ev >= min_n

    ext_mode, ext_live_ok = _external_checks(
        ext,
        allow_missing=args.allow_missing_external_status,
        allow_degraded_live=args.allow_external_degraded_for_live,
    )

    shadow_ready = shadow_has_score_rows
    live_ready = (
        shadow_ready and promotion_ok and hit_rate_ok and ext_live_ok
    )

    if live_ready:
        recommendation = "live_candidate"
    elif shadow_ready:
        recommendation = "shadow_candidate"
    else:
        recommendation = "defer"

    out_doc: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "inputs": {
            "promotion_gates_json": str(args.promotion_gates.resolve()),
            "hit_rate_json": str(args.hit_rate.resolve()),
            "external_status_json": str(args.external_status.resolve()),
            "score_json": str(args.score.resolve()),
            "min_hit_rate": min_r,
            "min_n": min_n,
            "allow_external_degraded_for_live": bool(args.allow_external_degraded_for_live),
            "allow_missing_external_status": bool(args.allow_missing_external_status),
        },
        "checks": {
            "shadow_has_score_rows": shadow_has_score_rows,
            "promotion_combined_all_passed": promotion_ok,
            "hit_rate_ok": hit_rate_ok,
            "hit_rate_observed": rate,
            "n_evaluated_observed": n_ev,
            "external_mode": ext_mode,
            "external_live_ok": ext_live_ok,
        },
        "result": {
            "shadow_ready": shadow_ready,
            "live_ready": live_ready,
            "recommendation": recommendation,
            "note": "B-track fast gate only. Human sign-off required before any A-track/live route.",
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
