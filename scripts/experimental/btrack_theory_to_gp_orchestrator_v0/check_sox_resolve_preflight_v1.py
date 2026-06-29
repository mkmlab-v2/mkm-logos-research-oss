#!/usr/bin/env python3
"""Preflight for Logos SOX general_prophecy resolve (B-track, no auto-resolve)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
OUT = ROOT / "reports/general_prophecy_sox_resolve_preflight_v1_latest.json"

SOX_QIDS = (
    "gp_2026_logos_sox_new_high_before_0930",
    "gp_2026_logos_sox_daily_drop_ge_5pct_q3",
    "gp_2026_logos_sox_close_below_ref_minus_10pct_by_0930",
)
DEADLINE = "2026-10-01T00:00:00Z"
CSV = ROOT / "research/market_data/sox_daily_external_yf.csv"


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
    items = []
    for qid in SOX_QIDS:
        q = next((x for x in doc.get("questions") or [] if x.get("question_id") == qid), None)
        status = (q.get("resolution") or {}).get("status", "pending") if q else "missing"
        items.append(
            {
                "question_id": qid,
                "in_registry": q is not None,
                "resolution_status": status,
                "resolution_deadline_utc": DEADLINE,
                "days_to_deadline": round((deadline - now).total_seconds() / 86400, 2) if deadline else None,
                "data_file_exists": CSV.is_file(),
                "resolve_ready_now": bool(deadline and now >= deadline and status == "pending" and CSV.is_file()),
            }
        )

    out_doc = {
        "schema": "general_prophecy_sox_resolve_preflight_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "now_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "questions": items,
        "preview_chain": "py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/resolve_sox_gp_v1.py",
        "apply_chain_when_ready": "py scripts/experimental/btrack_theory_to_gp_orchestrator_v0/resolve_sox_gp_v1.py --apply --run-brier",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ready = sum(1 for q in items if q.get("resolve_ready_now"))
    print(json.dumps({"ok": True, "resolve_ready_now": ready, "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
