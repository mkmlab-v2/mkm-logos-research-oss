#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promote holdout-learned candidate manifest to SSOT (B-track; backup + audit)."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SSOT = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"
CANDIDATE = ROOT / "reports/market_psych_manifest_candidate_holdout_best_v1.json"
VALIDATION = ROOT / "reports/market_psych_manifest_candidate_price_validation_v1_latest.json"
BACKUP_DIR = ROOT / "docs/final/artifacts/manifest_backups"
AUDIT_OUT = ROOT / "reports/market_psych_manifest_ssot_promotion_audit_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, default=CANDIDATE)
    ap.add_argument("--ssot", type=Path, default=SSOT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.candidate.is_file():
        print(f"missing {args.candidate}", file=sys.stderr)
        return 2
    if not args.ssot.is_file():
        print(f"missing {args.ssot}", file=sys.stderr)
        return 2

    old = _load(args.ssot)
    cand = _load(args.candidate)
    val = _load(VALIDATION) if VALIDATION.is_file() else {}

    learning = cand.pop("holdout_learning_v1", None) or {}
    profile_id = learning.get("profile_id") or "unknown"

    promoted = copy.deepcopy(cand)
    promoted["version"] = "2.0.1"
    promoted["notes_ko"] = (
        f"시장 per-date 레일 SSOT. {profile_id} holdout weights promoted "
        f"{_utc_now()[:10]}. 인간 DNA(AGCT)와 분리."
    )
    promoted["manifest_promotion_v1"] = {
        "promoted_at_utc": _utc_now(),
        "profile_id": profile_id,
        "source_candidate": str(args.candidate.relative_to(ROOT)).replace("\\", "/"),
        "holdout_learning": learning,
        "price_validation": val.get("delta_candidate_minus_ssot"),
        "validation_report": str(VALIDATION.relative_to(ROOT)).replace("\\", "/")
        if VALIDATION.is_file()
        else None,
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "a_track_autotrigger_forbidden": True,
    }

    ts = _utc_now().replace(":", "").replace("-", "")[:15]
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"market_psych_to_sasang_axis_manifest_v2_pre_{profile_id}_{ts}.json"
    audit = {
        "schema": "market_psych_manifest_ssot_promotion_audit_v1",
        "generated_at_utc": _utc_now(),
        "profile_id": profile_id,
        "backup_path": str(backup_path.relative_to(ROOT)).replace("\\", "/"),
        "ssot_path": str(args.ssot.relative_to(ROOT)).replace("\\", "/"),
        "dry_run": args.dry_run,
        "axis_raw_weights_before": old.get("axis_raw_weights"),
        "axis_raw_weights_after": promoted.get("axis_raw_weights"),
    }

    if args.dry_run:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 0

    backup_path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.ssot.write_text(json.dumps(promoted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/market_psych_manifest_ssot_promotion_audit_v1_latest.json"
    shutil.copy2(AUDIT_OUT, art)
    print(f"BACKUP: {backup_path.resolve()}")
    print(f"SSOT: {args.ssot.resolve()}")
    print(f"AUDIT: {AUDIT_OUT.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
