#!/usr/bin/env python3
"""Apply L3: copy B-track ST-U sqlite to production A-contract path (with backup).

Requires commander ACK_L3 in logos_rag_btrack_promotion_human_approval_v1_latest.json.
Does not touch VPS, prophecy gates, or Track A live trading.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PILOT = ROOT / "reports/constitution/btrack_pilot"
PROD_SQLITE = ART / "logos_vector_index_ann_lite_v1.sqlite"
PROD_REPORT = ART / "logos_vector_index_ann_lite_v1_latest.json"
ST_SQLITE = PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"
APPROVAL = ART / "logos_rag_btrack_promotion_human_approval_v1_latest.json"
DEFAULT_OUT = ART / "logos_rag_l3_production_swap_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_approval() -> dict[str, Any]:
    if not APPROVAL.is_file():
        raise SystemExit(f"Missing approval artifact: {APPROVAL}")
    doc = json.loads(APPROVAL.read_text(encoding="utf-8-sig"))
    if doc.get("tier") != "L3" or doc.get("decision") != "ACK_L3":
        raise SystemExit(
            f"Approval not ACK_L3 (tier={doc.get('tier')!r} decision={doc.get('decision')!r}). "
            "Run record_logos_rag_btrack_promotion_human_approval_v1.py --tier L3 --force first."
        )
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Plan only; no file writes.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-report-json", action="store_true", help="Do not patch v1_latest.json.")
    args = ap.parse_args()

    approval = _load_approval()
    if not ST_SQLITE.is_file():
        raise SystemExit(f"Missing B-track ST index: {ST_SQLITE}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_sqlite = ART / f"logos_vector_index_ann_lite_v1.sqlite.bak_{ts}"
    backup_report = ART / f"logos_vector_index_ann_lite_v1_latest.json.bak_{ts}"

    plan = {
        "source": str(ST_SQLITE.relative_to(ROOT)),
        "dest": str(PROD_SQLITE.relative_to(ROOT)),
        "backup_sqlite": str(backup_sqlite.relative_to(ROOT)),
        "backup_report": str(backup_report.relative_to(ROOT)) if PROD_REPORT.is_file() else None,
    }

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    PROD_SQLITE.parent.mkdir(parents=True, exist_ok=True)
    if PROD_SQLITE.is_file():
        shutil.copy2(PROD_SQLITE, backup_sqlite)
    if PROD_REPORT.is_file():
        shutil.copy2(PROD_REPORT, backup_report)

    shutil.copy2(ST_SQLITE, PROD_SQLITE)

    report_patched = False
    if not args.skip_report_json:
        base: dict[str, Any] = {}
        if PROD_REPORT.is_file():
            base = json.loads(PROD_REPORT.read_text(encoding="utf-8-sig"))
        base.update(
            {
                "ts_utc": _utc_now(),
                "embedding_backend": "sentence_transformers",
                "embedding_mode": "sentence_transformers_v1",
                "l3_swap": {
                    "applied": True,
                    "source_sqlite": plan["source"],
                    "backup_sqlite": plan["backup_sqlite"],
                    "approval_ts": approval.get("ts_utc"),
                },
                "notes": (
                    "L3 production swap from B-track ST-U index. "
                    "Rollback: restore .bak_* files. Not semantic quality proof."
                ),
            }
        )
        PROD_REPORT.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report_patched = True

    doc = {
        "schema": "logos_rag_l3_production_swap_v1",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "ok": True,
        "plan": plan,
        "report_json_patched": report_patched,
        "approval_ref": str(APPROVAL.relative_to(ROOT)),
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "a_track_live_trading": False,
            "vps_deploy": False,
            "rollback": f"Restore {plan['backup_sqlite']}",
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json), "prod": str(PROD_SQLITE)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
