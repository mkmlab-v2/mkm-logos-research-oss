#!/usr/bin/env python3
"""Unified preflight for Logos AI equity general_prophecy (SOX + NVDA + QQQ)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
OUT = ROOT / "reports/general_prophecy_logos_ai_equity_resolve_preflight_v1_latest.json"
DEADLINE = "2026-10-01T00:00:00Z"

QUESTIONS = (
    {
        "question_id": "gp_2026_logos_sox_new_high_before_0930",
        "csv": ROOT / "research/market_data/sox_daily_external_yf.csv",
        "preview": "resolve_sox_gp_v1.py",
    },
    {
        "question_id": "gp_2026_logos_sox_daily_drop_ge_5pct_q3",
        "csv": ROOT / "research/market_data/sox_daily_external_yf.csv",
        "preview": "resolve_sox_gp_v1.py",
    },
    {
        "question_id": "gp_2026_logos_sox_close_below_ref_minus_10pct_by_0930",
        "csv": ROOT / "research/market_data/sox_daily_external_yf.csv",
        "preview": "resolve_sox_gp_v1.py",
    },
    {
        "question_id": "gp_2026_logos_nvda_daily_drop_ge_7pct_q3",
        "csv": ROOT / "research/market_data/nvda_daily_external_yf.csv",
        "preview": "resolve_nvda_gp_v1.py",
    },
    {
        "question_id": "gp_2026_logos_qqq_new_high_before_0930",
        "csv": ROOT / "research/market_data/qqq_daily_external_yf.csv",
        "preview": "resolve_qqq_gp_v1.py",
    },
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    deadline = _parse_utc(DEADLINE)
    doc = json.loads(args.registry.read_text(encoding="utf-8-sig"))
    items: list[dict] = []
    for spec in QUESTIONS:
        qid = spec["question_id"]
        q = next((x for x in doc.get("questions") or [] if x.get("question_id") == qid), None)
        status = (q.get("resolution") or {}).get("status", "pending") if q else "missing"
        csv_path: Path = spec["csv"]
        items.append(
            {
                "question_id": qid,
                "in_registry": q is not None,
                "resolution_status": status,
                "resolution_deadline_utc": DEADLINE,
                "days_to_deadline": round((deadline - now).total_seconds() / 86400, 2) if deadline else None,
                "data_file_exists": csv_path.is_file(),
                "preview_chain": f"py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/{spec['preview']}",
                "resolve_ready_now": bool(deadline and now >= deadline and status == "pending" and csv_path.is_file()),
            }
        )

    out_doc = {
        "schema": "general_prophecy_logos_ai_equity_resolve_preflight_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "now_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "questions": items,
        "batch_preview": "py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/run_logos_ai_equity_gp_resolve_preview_v1.py",
        "batch_apply_when_ready": "py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/run_logos_ai_equity_gp_resolve_preview_v1.py --apply --run-brier",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = sum(1 for q in items if q.get("resolve_ready_now"))
    print(json.dumps({"ok": True, "resolve_ready_now": ready, "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
