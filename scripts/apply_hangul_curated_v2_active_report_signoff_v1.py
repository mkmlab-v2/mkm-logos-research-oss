#!/usr/bin/env python3
"""Apply v2 ACTIVE candidate → MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT (MS HOLD)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_active_promotion_signoff_v1_latest.json"
CANDIDATE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_HANGUL_CURATED_V2_CANDIDATE.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
APPLY_LOG = ROOT / "reports/hangul_curated_v2_active_report_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SIGNOFF.is_file() or not json.loads(SIGNOFF.read_text(encoding="utf-8")).get("approved"):
        print("ABORT: v2 active signoff missing or not approved")
        return 1
    if not CANDIDATE.is_file():
        print("ABORT: v2 ACTIVE candidate missing")
        return 1

    backup = ACTIVE.with_name(f"MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.pre_v2_active_{_stamp()}.json")
    plan = {
        "active_path": str(ACTIVE.relative_to(ROOT)).replace("\\", "/"),
        "candidate_path": str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"),
        "backup_path": str(backup.relative_to(ROOT)).replace("\\", "/"),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    if ACTIVE.is_file():
        shutil.copy2(ACTIVE, backup)

    shutil.copy2(CANDIDATE, ACTIVE)

    m = (json.loads(CANDIDATE.read_text(encoding="utf-8")).get("compression_metrics") or {})
    log = {
        "schema": "hangul_curated_v2_active_report_apply_v1",
        "applied_at_utc": _utc(),
        "plan": plan,
        "compression_metrics": {
            "global_token_saving_rate": m.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": m.get("avg_reconstruction_fidelity_jaccard"),
        },
        "ms_paste_headline": "HOLD",
        "raw_repair_note": "Bench ACTIVE KPI updated; MS external 47.5%/0.890 unchanged per FAIL-COMP-004.",
    }
    APPLY_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "backup": plan["backup_path"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
