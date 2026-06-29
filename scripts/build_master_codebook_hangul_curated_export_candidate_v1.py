#!/usr/bin/env python3
"""Materialize export candidate lexicon from curated overlay ([HYPO], not production SSOT)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT = ROOT / "reports/constitution/btrack_pilot"
BASE = PILOT / "master_codebook_lexicon_v1_41658_rows_latest.json"
OVERLAY_DEFAULT = PILOT / "master_codebook_lexicon_v1_41658_hangul_curated_overlay.json"
EXPORT_SIGNOFF = ROOT / "reports/hangul_lexicon_export_merge_signoff_v1_latest.json"
DEFAULT_OUT = PILOT / "master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json"
REPORT = ROOT / "reports/hangul_lexicon_export_candidate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ko_count(doc: dict) -> int:
    return sum(1 for e in doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--overlay", type=Path, default=None, help="Curated overlay JSON (default: v1 overlay).")
    ap.add_argument(
        "--base-lexicon",
        type=Path,
        default=BASE,
        help="Baseline lexicon for export_candidate_meta (default 41658).",
    )
    ap.add_argument("--require-export-signoff", action="store_true", default=True)
    ap.add_argument("--no-require-export-signoff", action="store_false", dest="require_export_signoff")
    args = ap.parse_args()
    overlay_path = (args.overlay or OVERLAY_DEFAULT).resolve()
    base_path = args.base_lexicon if args.base_lexicon.is_absolute() else (ROOT / args.base_lexicon)
    base_path = base_path.resolve()
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    if args.require_export_signoff:
        if not EXPORT_SIGNOFF.is_file():
            print("ABORT: export merge signoff missing")
            return 1
        sig = json.loads(EXPORT_SIGNOFF.read_text(encoding="utf-8"))
        if not sig.get("approved"):
            print("ABORT: export merge signoff not approved")
            return 1

    if not overlay_path.is_file() or not base_path.is_file():
        print("ABORT: curated overlay or base missing", overlay_path, base_path)
        return 1

    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    base_n = json.loads(base_path.read_text(encoding="utf-8")).get("row_count") or 41658
    ko_n = _ko_count(overlay)
    expected = int(base_n) + ko_n if ko_n else int(base_n)

    payload = dict(overlay)
    payload["generated_at_utc"] = _utc()
    payload["export_candidate_meta"] = {
        "schema": "master_codebook_hangul_curated_export_candidate_v1",
        "research_only": True,
        "track_a_active_write": False,
        "production_ssot_swap": False,
        "source_overlay": str(overlay_path.relative_to(ROOT)).replace("\\", "/"),
        "base_production_lexicon": str(base_path.relative_to(ROOT)).replace("\\", "/"),
        "base_row_count": int(base_n),
        "ko_rows_merged": ko_n,
        "candidate_row_count": len(payload.get("entries") or []),
    }
    payload["row_count"] = payload["export_candidate_meta"]["candidate_row_count"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    report = {
        "schema": "hangul_lexicon_export_candidate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "candidate_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "row_count": payload["row_count"],
        "ko_rows": ko_n,
        "export_candidate_meta": payload["export_candidate_meta"],
        "verdict": {
            "ready_for_pilot_recheck": True,
            "promote_production_ssot": False,
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(out_path), "row_count": payload["row_count"], "ko_rows": ko_n},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
