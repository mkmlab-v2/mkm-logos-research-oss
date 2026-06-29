#!/usr/bin/env python3
"""Preflight for Logos 2026 general_prophecy resolve chain (B-track, no auto-resolve)."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
OUT = ROOT / "reports/general_prophecy_logos_june_resolve_preflight_v1_latest.json"

LOGOS_QIDS = (
    "gp_2026_logos_kospi_close_below_8500_by_0630",
    "gp_2026_logos_nasdaq_daily_drop_ge_3pct_june",
    "gp_2026_logos_brent_spot_ge_95_before_0701",
    "gp_2026_logos_vix_close_ge_25_june",
)

DATA_PATHS = {
    "gp_2026_logos_kospi_close_below_8500_by_0630": ROOT / "research/market_data/kospi_daily_external_yf.csv",
    "gp_2026_logos_nasdaq_daily_drop_ge_3pct_june": ROOT / "research/market_data/nasdaq_daily_external_yf.csv",
    "gp_2026_logos_brent_spot_ge_95_before_0701": ROOT / "research/market_data/brent_daily_external.csv",
    "gp_2026_logos_vix_close_ge_25_june": ROOT / "research/market_data/vix_daily_external_yf.csv",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _csv_last_date(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    for key in ("Date", "date", "Datetime"):
        if key in rows[-1]:
            return str(rows[-1][key])[:10]
    return None


def preflight(*, registry: Path, now: datetime) -> dict:
    doc = json.loads(registry.read_text(encoding="utf-8-sig"))
    items: list[dict] = []
    for qid in LOGOS_QIDS:
        q = next((x for x in doc.get("questions") or [] if x.get("question_id") == qid), None)
        if q is None:
            items.append({"question_id": qid, "ok": False, "error": "missing_in_registry"})
            continue
        deadline = _parse_utc(str(q.get("resolution_deadline_utc") or ""))
        status = (q.get("resolution") or {}).get("status", "pending")
        data_path = DATA_PATHS.get(qid)
        data_exists = data_path.is_file() if data_path else False
        last_row = _csv_last_date(data_path) if data_path and data_exists else None
        days_to_deadline = (deadline - now).total_seconds() / 86400 if deadline else None
        resolve_ready = bool(deadline and now >= deadline and status == "pending" and data_exists)
        items.append(
            {
                "question_id": qid,
                "resolution_status": status,
                "resolution_deadline_utc": q.get("resolution_deadline_utc"),
                "days_to_deadline": round(days_to_deadline, 2) if days_to_deadline is not None else None,
                "data_path": str(data_path.relative_to(ROOT)).replace("\\", "/") if data_path else None,
                "data_file_exists": data_exists,
                "data_last_date": last_row,
                "resolve_ready_now": resolve_ready,
                "early_resolve_blocked": not resolve_ready,
            }
        )
    return {
        "schema": "general_prophecy_logos_june_resolve_preflight_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "now_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "questions": items,
        "chain_when_ready": [
            "py scripts/resolve_general_prophecy_question_v1.py -i docs/final/artifacts/general_prophecy_latest.json --in-place --question-id <id> --resolution-status resolved --outcome true|false",
            "py scripts/eval_general_prophecy_brier_score.py",
            "py scripts/build_general_prophecy_explainable_v1.py",
        ],
        "track_wall": {"a_track_auto_promotion": False, "live_trading": False},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()
    doc = preflight(registry=args.registry, now=datetime.now(timezone.utc))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = sum(1 for q in doc["questions"] if q.get("resolve_ready_now"))
    print(json.dumps({"ok": True, "resolve_ready_now": ready, "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
