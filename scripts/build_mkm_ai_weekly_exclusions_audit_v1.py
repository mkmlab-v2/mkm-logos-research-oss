#!/usr/bin/env python3
"""Emit one-line audit memo for weekly readiness exclusions (promotion gate evidence)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_ai_v2_weekly_exclusions_audit_v1_latest.json"
EXCLUSIONS = ROOT / "scripts/mkm_ai_v2_weekly_readiness_exclusions_v1.json"
WEEKLY = ROOT / "docs/final/artifacts/mkm_ai_v2_weekly_readiness_report_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    excl_path = EXCLUSIONS if EXCLUSIONS.is_file() else None
    weekly_path = WEEKLY if WEEKLY.is_file() else None
    exclusions: list[dict[str, str]] = []
    notes = ""
    if excl_path:
        raw = json.loads(excl_path.read_text(encoding="utf-8-sig"))
        exclusions = list(raw.get("exclusions") or [])
        notes = str(raw.get("notes", ""))

    weekly = {}
    if weekly_path:
        weekly = json.loads(weekly_path.read_text(encoding="utf-8-sig"))

    excluded_audit = weekly.get("excluded_from_stats") or []
    summary_ko = (
        "주간 pass_rate 집계에서 제외된 행은 로그 원본은 유지하고, "
        "pre-fix MCP 정렬(hostinger MCP 제거·openchrome optional) 이전 실패·일회성 실패만 통계에서 빼 재현 가능한 승격 판정을 맞춘 것."
    )
    one_liner = (
        f"weekly {weekly.get('pass_rate_percent', '?')}% "
        f"({weekly.get('pass_count', '?')}/{weekly.get('sample_count', '?')}); "
        f"{len(excluded_audit)} audited exclusions; raw log unchanged."
    )

    return {
        "schema": "mkm_ai_v2_weekly_exclusions_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": False,
        "policy": "exclusions affect rolling weekly stats only; not raw log deletion",
        "exclusions_source": str(excl_path) if excl_path else None,
        "weekly_report_source": str(weekly_path) if weekly_path else None,
        "exclusion_count": len(exclusions),
        "excluded_from_stats_count": len(excluded_audit),
        "notes_from_policy_file": notes,
        "summary_ko": summary_ko,
        "one_liner": one_liner,
        "exclusions": exclusions,
        "excluded_from_stats_mirror": excluded_audit,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "one_liner": doc["one_liner"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
