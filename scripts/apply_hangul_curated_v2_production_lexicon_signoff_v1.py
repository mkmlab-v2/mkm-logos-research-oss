#!/usr/bin/env python3
"""Apply v2 lexicon → production SSOT (41708_rows_latest; ACTIVE unchanged)."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_track_a_lexicon_promotion_signoff_v1_latest.json"
CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v2.json"
)
PILOT = ROOT / "reports/constitution/btrack_pilot"
PREV_PROD = PILOT / "master_codebook_lexicon_v1_41687_rows_latest.json"
NEW_PROD = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
POINTER = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
APPLY_LOG = ROOT / "reports/hangul_curated_v2_production_lexicon_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--candidate",
        type=Path,
        default=CANDIDATE,
        help="Export candidate lexicon JSON (default: v2 41708 full).",
    )
    ap.add_argument(
        "--new-production",
        type=Path,
        default=NEW_PROD,
        help="Production SSOT path to write (default: 41708_rows_latest).",
    )
    ap.add_argument("--wave", type=str, default="v2_50_lemmas")
    args = ap.parse_args()

    candidate_path = args.candidate if args.candidate.is_absolute() else (ROOT / args.candidate)
    new_prod_path = args.new_production if args.new_production.is_absolute() else (ROOT / args.new_production)

    if not SIGNOFF.is_file():
        print("ABORT: v2 lexicon signoff missing")
        return 1
    sig = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    if not sig.get("approved"):
        print("ABORT: v2 signoff not approved")
        return 1
    if not candidate_path.is_file():
        print("ABORT: v2 export candidate missing")
        return 1

    active_before = ACTIVE.read_bytes() if ACTIVE.is_file() else None
    archive_prev = PILOT / f"master_codebook_lexicon_v1_41687_rows_archived_{_stamp()}_pre_v2_curated.json"

    plan = {
        "archive_previous_production_41687": str(archive_prev.relative_to(ROOT)).replace("\\", "/"),
        "new_production_path": str(new_prod_path.relative_to(ROOT)).replace("\\", "/"),
        "source_candidate": str(candidate_path.relative_to(ROOT)).replace("\\", "/"),
        "superseded_production_41687": str(PREV_PROD.relative_to(ROOT)).replace("\\", "/") if PREV_PROD.is_file() else None,
        "wave": args.wave,
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    if PREV_PROD.is_file():
        shutil.copy2(PREV_PROD, archive_prev)

    shutil.copy2(candidate_path, new_prod_path)

    cand_doc = json.loads(candidate_path.read_text(encoding="utf-8"))
    ko_n = sum(1 for e in cand_doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")
    row_count = cand_doc.get("row_count") or len(cand_doc.get("entries") or [])

    if POINTER.is_file():
        ptr = json.loads(POINTER.read_text(encoding="utf-8"))
        prev_prod = ptr.get("production_ssot") or {}
        ptr["generated_at_utc"] = _utc()
        ptr["production_ssot"] = {
            "role": f"Track A bench · Hangul curated lexicon v2 ({row_count} rows)",
            "path": plan["new_production_path"],
            "row_count": row_count,
            "golden40_kpi": prev_prod.get("golden40_kpi") or {},
            "ms_paste_headline": "HOLD",
            "previous_production_archived_41687": plan["archive_previous_production_41687"],
            "ko_rows": ko_n,
            "hangul_curated_v2_signoff": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "wave": args.wave,
        }
        ptr["archived_41687_pre_v2_curated"] = {
            "role": "Pre-v2 production (29 ko)",
            "path": plan["archive_previous_production_41687"],
            "row_count": 41687,
        }
        ptr["fail_comp_004"] = (
            "ACTIVE report not updated by apply_hangul_curated_v2_production_lexicon_signoff_v1."
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
        "schema": "hangul_curated_v2_production_lexicon_apply_v1",
        "applied_at_utc": _utc(),
        "plan": plan,
        "active_report_bytes_unchanged": active_unchanged,
        "pointer_refreshed": POINTER.is_file(),
    }
    APPLY_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "new_production": plan["new_production_path"], "archived_41687": plan["archive_previous_production_41687"]},
            ensure_ascii=False,
        )
    )
    return 0 if active_unchanged else 3


if __name__ == "__main__":
    raise SystemExit(main())
