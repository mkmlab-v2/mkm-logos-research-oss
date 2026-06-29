#!/usr/bin/env python3
"""Append weekly domain prophecy portfolio digest JSONL [research_only · HOLD]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/commander/domain_prophecy_registry_v1.json"
LOOP_ART = ROOT / "reports/domain_prophecy_daily_loop_v1_latest.json"
SMOKE_ART = ROOT / "reports/domain_prophecy_smoke_coverage_v1_latest.json"
ROUTE_ART = ROOT / "reports/domain_prophecy_shallow_route_v1_latest.json"
LOG = ROOT / "reports/domain_prophecy_weekly_digest_v1.jsonl"
OUT = ROOT / "reports/domain_prophecy_weekly_digest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--log", type=Path, default=LOG)
    args = ap.parse_args()

    registry = _load_optional(REGISTRY)
    loop_doc = _load_optional(LOOP_ART)
    smoke_doc = _load_optional(SMOKE_ART)

    domains = registry.get("domains") or []
    by_phase: dict[str, int] = {}
    by_archetype: dict[str, int] = {}
    active = 0
    for row in domains:
        if not isinstance(row, dict):
            continue
        if row.get("status") in ("active", "active_shadow", "active_regression", "active_smoke"):
            active += 1
        ph = str(row.get("phase") or "?")
        ar = str(row.get("archetype") or "?")
        by_phase[ph] = by_phase.get(ph, 0) + 1
        by_archetype[ar] = by_archetype.get(ar, 0) + 1

    digest = {
        "schema": "domain_prophecy_weekly_digest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "production_apply_authorized": False,
        "portfolio": {
            "domain_count": len(domains),
            "active_count": active,
            "by_phase": by_phase,
            "by_archetype": by_archetype,
        },
        "signals": {
            "daily_loop_quality_ok": loop_doc.get("quality_ok"),
            "daily_loop_domains": len(loop_doc.get("domains") or []),
            "smoke_coverage_ok": smoke_doc.get("ok"),
            "smoke_mapped_count": smoke_doc.get("smoke_mapped_count"),
        },
        "pointers": {
            "registry": "data/commander/domain_prophecy_registry_v1.json",
            "schedule": "docs/final/artifacts/mkm_multi_domain_prophecy_hd_schedule_v1_latest.json",
            "router_map": "data/commander/domain_prophecy_shallow_router_map_v1.json",
        },
        "reproduce": "py scripts/build_domain_prophecy_weekly_digest_v1.py",
        "note_ko": "research_only 포트폴리오 리뷰; Track A 승격 주장 금지",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/domain_prophecy_weekly_digest_v1_latest.json"
    art.write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with args.log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(digest, ensure_ascii=False) + "\n")

    print(json.dumps({"ok": True, "active_count": active}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
