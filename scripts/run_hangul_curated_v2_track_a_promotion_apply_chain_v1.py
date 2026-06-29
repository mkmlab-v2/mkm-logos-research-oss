#!/usr/bin/env python3
"""v2 lexicon promotion: packet → signoff → apply (commander; ACTIVE/MS HOLD)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES: dict[str, dict[str, str]] = {
    "v2": {
        "prep": "reports/hangul_curated_v2_export_prep_packet_v1_latest.json",
        "candidate": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v2.json",
        "pilot_json": "reports/lexicon_hangul_curated_pilot_v2_latest.json",
        "base_lexicon": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json",
        "packet_out": "reports/hangul_curated_v2_track_a_promotion_packet_v1_latest.json",
        "wave": "v2_50_lemmas",
        "signoff_note": "commander approved v2 50-lemma lexicon swap",
    },
    "v2_human": {
        "prep": "reports/hangul_curated_v2_human_export_prep_packet_v1_latest.json",
        "candidate": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v2_human.json",
        "pilot_json": "reports/lexicon_hangul_curated_pilot_v2_human_export_candidate_latest.json",
        "base_lexicon": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json",
        "packet_out": "reports/hangul_curated_v2_human_track_a_promotion_packet_v1_latest.json",
        "wave": "v2_human_6_lemmas",
        "signoff_note": "commander approved v2_human 6-lemma export candidate → production SSOT",
    },
}


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commander-v2-lexicon-approve", action="store_true")
    ap.add_argument("--dry-run-apply", action="store_true")
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default="v2",
        help="Path preset (v2_human = Wave2 human pick 6 on 41708 baseline).",
    )
    ap.add_argument("--note", default="", help="Override signoff note.")
    args = ap.parse_args()
    prof = PROFILES[args.profile]
    note = args.note.strip() or prof["signoff_note"]

    py = sys.executable
    rc = _run(
        [
            py,
            "scripts/build_hangul_curated_v2_track_a_promotion_packet_v1.py",
            "--prep",
            prof["prep"],
            "--candidate",
            prof["candidate"],
            "--pilot-json",
            prof["pilot_json"],
            "--base-lexicon",
            prof["base_lexicon"],
            "--wave",
            prof["wave"],
            "--out",
            prof["packet_out"],
        ]
    )
    if rc != 0 and rc != 2:
        return rc
    if args.commander_v2_lexicon_approve:
        if rc == 2:
            print("ABORT: promotion_ready=false")
            return 2
        rc = _run(
            [
                py,
                "scripts/record_hangul_curated_v2_track_a_lexicon_promotion_signoff_v1.py",
                "--commander-v2-lexicon-approve",
                "--packet",
                prof["packet_out"],
                "--note",
                note,
            ]
        )
        if rc != 0:
            return rc
        apply_cmd = [
            py,
            "scripts/apply_hangul_curated_v2_production_lexicon_signoff_v1.py",
            "--candidate",
            prof["candidate"],
            "--wave",
            prof["wave"],
        ]
        if args.dry_run_apply:
            apply_cmd.append("--dry-run")
        rc = _run(apply_cmd)
        if rc != 0:
            return rc
        rc = _run([py, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"])

    print(
        __import__("json").dumps(
            {"OK": "v2_track_a_promotion_apply_chain complete", "profile": args.profile},
            ensure_ascii=False,
        )
    )
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    raise SystemExit(main())
