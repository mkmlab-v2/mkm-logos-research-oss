#!/usr/bin/env python3
"""Preflight for BLS May-2026 unemployment general_prophecy resolve (B-track, no auto-resolve)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
OUT = ROOT / "reports/general_prophecy_bls_unrate_resolve_preflight_v1_latest.json"
QID = "seed.macro.us_bls_unrate_gt_43_20260606"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def preflight(*, registry: Path, now: datetime) -> dict:
    doc = json.loads(registry.read_text(encoding="utf-8-sig"))
    q = next((x for x in doc.get("questions") or [] if x.get("question_id") == QID), None)
    if q is None:
        return {"schema": "general_prophecy_bls_unrate_resolve_preflight_v1", "ok": False, "error": "missing_question"}
    deadline = _parse_utc(str(q.get("resolution_deadline_utc") or ""))
    status = (q.get("resolution") or {}).get("status", "pending")
    days = (deadline - now).total_seconds() / 86400 if deadline else None
    resolve_ready = bool(deadline and now >= deadline and status == "pending")
    return {
        "schema": "general_prophecy_bls_unrate_resolve_preflight_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "question_id": QID,
        "resolution_status": status,
        "resolution_deadline_utc": q.get("resolution_deadline_utc"),
        "days_to_deadline": round(days, 2) if days is not None else None,
        "resolve_ready_now": resolve_ready,
        "resolve_hint": (
            "After BLS Employment Situation May 2026 release: compare seasonally adjusted "
            "unemployment rate to 4.3% (strictly greater -> true)."
        ),
        "chain_when_ready": [
            f"py scripts/resolve_general_prophecy_question_v1.py -i {REGISTRY.relative_to(ROOT)} "
            "--in-place --question-id seed.macro.us_bls_unrate_gt_43_20260606 "
            "--resolution-status resolved --outcome true|false --notes \"BLS May 2026 SA unrate\" "
            "--evidence-uri https://www.bls.gov/news.release/empsit.nr0.htm",
            "py scripts/eval_general_prophecy_brier_score.py",
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
    print(json.dumps({"ok": True, "resolve_ready_now": doc.get("resolve_ready_now"), "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
