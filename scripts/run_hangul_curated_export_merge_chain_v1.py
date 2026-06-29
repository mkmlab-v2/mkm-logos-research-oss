#!/usr/bin/env python3
"""H2: export candidate + pilot recheck after export-merge commander approval."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_SIGNOFF = ROOT / "reports/hangul_lexicon_export_merge_signoff_v1_latest.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"
CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json"
)
PROFILES: dict[str, dict[str, str]] = {
    "v1": {
        "overlay": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay.json",
        "candidate": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41687_hangul_curated_export_candidate_v1.json",
        "base_lexicon": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json",
        "manifest": "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json",
        "pilot_out": "reports/lexicon_hangul_curated_pilot_v1_latest.json",
    },
    "v2_human": {
        "overlay": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_overlay_v2_human.json",
        "candidate": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v2_human.json",
        "base_lexicon": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json",
        "manifest": "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2_human.json",
        "pilot_out": "reports/lexicon_hangul_curated_pilot_v2_human_export_candidate_latest.json",
    },
}


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-export-merge-approve",
        action="store_true",
        help="Record export-merge signoff then run chain.",
    )
    ap.add_argument(
        "--profile",
        choices=sorted(PROFILES.keys()),
        default="v1",
        help="Path preset (default v1; v2_human = Wave2 human pick 6 on 41708 baseline).",
    )
    ap.add_argument("--note", default="", help="Commander note recorded on export-merge signoff.")
    args = ap.parse_args()
    prof = PROFILES[args.profile]
    candidate = ROOT / prof["candidate"]

    py = sys.executable
    if args.commander_export_merge_approve:
        signoff_cmd = [
            py,
            "scripts/record_hangul_lexicon_export_merge_signoff_v1.py",
            "--commander-export-merge-approve",
        ]
        if args.note.strip():
            signoff_cmd.extend(["--note", args.note.strip()])
        rc = _run(signoff_cmd)
        if rc != 0:
            return rc

    if not EXPORT_SIGNOFF.is_file():
        print("ABORT: export merge signoff missing")
        return 1
    import json

    if not json.loads(EXPORT_SIGNOFF.read_text(encoding="utf-8")).get("approved"):
        print("ABORT: export merge signoff not approved")
        return 1

    steps = [
        (
            "export_candidate",
            [
                py,
                "scripts/build_master_codebook_hangul_curated_export_candidate_v1.py",
                "--overlay",
                prof["overlay"],
                "--out",
                prof["candidate"],
                "--base-lexicon",
                prof["base_lexicon"],
            ],
        ),
        (
            "pilot_on_candidate",
            [
                py,
                "scripts/run_hangul_curated_ingest_pilot_v1.py",
                "--manifest",
                prof["manifest"],
                "--overlay-path",
                prof["candidate"],
                "--base-lexicon",
                prof["base_lexicon"],
                "--out-json",
                prof["pilot_out"],
                "--skip-rebuild-overlay",
            ],
        ),
        ("pointer", [py, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"]),
        ("readiness_refresh", [py, "scripts/build_hangul_lexicon_ingest_pipeline_readiness_v1.py"]),
    ]
    for name, cmd in steps:
        rc = _run(cmd)
        if rc != 0:
            print(f"FAIL at {name} exit={rc}")
            return rc

    print(json.dumps({"OK": "export_merge_chain complete", "profile": args.profile, "candidate": prof["candidate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
