#!/usr/bin/env python3
"""Apply Track A lexicon production_ssot swap after commander sign-off (not ACTIVE)."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_track_a_lexicon_promotion_signoff_v1_latest.json"
CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json"
)
PILOT = ROOT / "reports/constitution/btrack_pilot"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
NEW_PROD = PILOT / "master_codebook_lexicon_v1_41687_rows_latest.json"
POINTER = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
APPLY_LOG = ROOT / "reports/hangul_curated_production_lexicon_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not SIGNOFF.is_file():
        print("ABORT: Track A lexicon signoff missing")
        return 1
    sig = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    if not sig.get("approved"):
        print("ABORT: signoff not approved")
        return 1
    if not CANDIDATE.is_file():
        print("ABORT: export candidate missing")
        return 1

    active_before = ACTIVE.read_bytes() if ACTIVE.is_file() else None
    archive_base = PILOT / f"master_codebook_lexicon_v1_41658_rows_archived_{_stamp()}_pre_hangul_curated.json"

    plan = {
        "archive_previous_production": str(archive_base.relative_to(ROOT)).replace("\\", "/"),
        "new_production_path": str(NEW_PROD.relative_to(ROOT)).replace("\\", "/"),
        "source_candidate": str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"),
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    if BASE.is_file():
        shutil.copy2(BASE, archive_base)

    shutil.copy2(CANDIDATE, NEW_PROD)

    cand_doc = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    ko_n = sum(1 for e in cand_doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")

    if POINTER.is_file():
        ptr = json.loads(POINTER.read_text(encoding="utf-8"))
        prev = ptr.get("production_ssot") or {}
        ptr["generated_at_utc"] = _utc()
        ptr["production_ssot"] = {
            "role": "Track A bench · Hangul curated lexicon (41658+ko)",
            "path": plan["new_production_path"],
            "row_count": cand_doc.get("row_count") or len(cand_doc.get("entries") or []),
            "golden40_kpi": (prev.get("golden40_kpi") or {}),
            "ms_paste_headline": prev.get("ms_paste_headline"),
            "previous_production_archived": plan["archive_previous_production"],
            "ko_rows": ko_n,
            "hangul_curated_promotion_signoff": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
        }
        ptr["archived_41658_pre_hangul_curated"] = {
            "role": "Pre-swap production backup",
            "path": plan["archive_previous_production"],
            "row_count": 41658,
        }
        ptr["fail_comp_004"] = (
            "ACTIVE report not updated by apply_hangul_curated_production_lexicon_signoff_v1."
        )
        POINTER.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    active_after = ACTIVE.read_bytes() if ACTIVE.is_file() else None
    active_unchanged = active_before == active_after

    from scripts.core.master_codebook_lexicon_v1_bridge import clear_codebook_cache

    clear_codebook_cache()

    import subprocess

    subprocess.call([sys.executable, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"], cwd=str(ROOT))
    clear_codebook_cache()

    log = {
        "schema": "hangul_curated_production_lexicon_apply_v1",
        "applied_at_utc": _utc(),
        "plan": plan,
        "active_report_bytes_unchanged": active_unchanged,
        "pointer_refreshed": POINTER.is_file(),
    }
    APPLY_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "new_production": plan["new_production_path"], "archived": plan["archive_previous_production"]}, ensure_ascii=False))
    return 0 if active_unchanged else 3


if __name__ == "__main__":
    raise SystemExit(main())
