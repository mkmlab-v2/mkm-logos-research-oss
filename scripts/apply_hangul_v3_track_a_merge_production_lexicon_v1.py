#!/usr/bin/env python3
"""Apply v3 Track A merge candidate → production 41708_rows_latest (ACTIVE unchanged)."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SIGNOFF = ROOT / "docs/final/artifacts/hangul_v3_track_a_merge_commander_signoff_v1_latest.json"
CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v3_track_a_merge_preflight.json"
)
PACKET = ROOT / "reports/hangul_v3_track_a_merge_preflight_packet_v1_latest.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"
PROD = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
POINTER = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
APPLY_LOG = ROOT / "reports/hangul_v3_track_a_merge_production_lexicon_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--candidate", type=Path, default=CANDIDATE)
    ap.add_argument("--wave", default="v3_track_a_merge_ko50")
    args = ap.parse_args()

    candidate_path = args.candidate if args.candidate.is_absolute() else (ROOT / args.candidate)
    if not SIGNOFF.is_file():
        print("ABORT: v3 merge signoff missing")
        return 1
    sig = json.loads(SIGNOFF.read_text(encoding="utf-8"))
    if not sig.get("approved"):
        print("ABORT: v3 merge signoff not approved")
        return 1
    if not candidate_path.is_file() or not PROD.is_file():
        print("ABORT: merge candidate or production lexicon missing")
        return 1

    packet = json.loads(PACKET.read_text(encoding="utf-8")) if PACKET.is_file() else {}
    g40 = (packet.get("golden40_compare") or {}).get("merge_candidate") or {}

    archive_prev = PILOT / f"master_codebook_lexicon_v1_41708_rows_archived_{_stamp()}_pre_v3_track_a_merge.json"
    plan = {
        "archive_previous_production": _rel(archive_prev),
        "new_production_path": _rel(PROD),
        "source_candidate": _rel(candidate_path),
        "wave": args.wave,
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, ensure_ascii=False))
        return 0

    active_before = ACTIVE.read_bytes() if ACTIVE.is_file() else None
    shutil.copy2(PROD, archive_prev)
    shutil.copy2(candidate_path, PROD)

    cand_doc = json.loads(candidate_path.read_text(encoding="utf-8"))
    ko_n = sum(1 for e in cand_doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")
    row_count = int(cand_doc.get("row_count") or len(cand_doc.get("entries") or []))

    if POINTER.is_file():
        ptr = json.loads(POINTER.read_text(encoding="utf-8"))
        prev_prod = ptr.get("production_ssot") or {}
        ptr["generated_at_utc"] = _utc()
        ptr["production_ssot"] = {
            **prev_prod,
            "role": f"Track A bench · Hangul v3 merge ({row_count} rows · ko {ko_n})",
            "path": plan["new_production_path"],
            "row_count": row_count,
            "ko_rows": ko_n,
            "golden40_kpi": {
                "global_token_saving_rate": g40.get("global_token_saving_rate"),
                "avg_reconstruction_fidelity_jaccard": g40.get("avg_reconstruction_fidelity_jaccard"),
                "case_count": g40.get("case_count", 40),
            },
            "ms_paste_headline": "HOLD",
            "apply_log": _rel(APPLY_LOG),
            "track_a_lexicon_signoff": _rel(SIGNOFF),
            "wave": args.wave,
            "previous_production_archived_pre_v3_merge": plan["archive_previous_production"],
            "merge_profile": (cand_doc.get("export_candidate_meta") or {}).get("merge_profile"),
        }
        ptr["export_candidate_hangul_v3_track_a_merge"] = {
            "role": "Applied v3 Track A merge candidate (41708 base + v2 overlay + v3 evidence)",
            "path": plan["source_candidate"],
            "row_count": row_count,
            "ko_rows": ko_n,
            "promotion": "APPLIED",
        }
        ptr["fail_comp_004"] = (
            "ACTIVE report not updated by apply_hangul_v3_track_a_merge_production_lexicon_v1."
        )
        POINTER.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    active_after = ACTIVE.read_bytes() if ACTIVE.is_file() else None
    active_unchanged = active_before == active_after

    from scripts.core.master_codebook_lexicon_v1_bridge import clear_codebook_cache

    clear_codebook_cache()

    log = {
        "schema": "hangul_v3_track_a_merge_production_lexicon_apply_v1",
        "applied_at_utc": _utc(),
        "plan": plan,
        "ko_rows": ko_n,
        "row_count": row_count,
        "active_report_bytes_unchanged": active_unchanged,
        "pointer_updated": POINTER.is_file(),
        "send_gate": "HOLD",
    }
    APPLY_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "new_production": plan["new_production_path"],
                "archived": plan["archive_previous_production"],
                "ko_rows": ko_n,
                "row_count": row_count,
            },
            ensure_ascii=False,
        )
    )
    return 0 if active_unchanged else 3


if __name__ == "__main__":
    raise SystemExit(main())
