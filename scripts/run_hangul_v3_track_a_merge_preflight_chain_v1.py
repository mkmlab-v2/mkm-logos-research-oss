#!/usr/bin/env python3
"""Track A v3 merge preflight chain — build candidate, pilot recheck, packet, gate (no prod swap)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports/constitution/btrack_pilot"
CANDIDATE = PILOT / "master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v3_track_a_merge_preflight.json"
V2_MANIFEST = "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json"
PROD = "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json"


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--profile",
        default="production_union_v2_full_on_base",
        choices=("production_union_v2_full_on_base", "production_preserve_v3_metadata_refresh"),
    )
    ap.add_argument("--skip-pilot", action="store_true")
    ap.add_argument("--enforce-gate", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str]]] = [
        (
            "merge_candidate_build",
            [
                py,
                "scripts/build_hangul_v3_track_a_merge_candidate_v1.py",
                "--profile",
                args.profile,
            ],
        ),
    ]

    if not args.skip_pilot:
        steps.append(
            (
                "pilot_on_merge_candidate",
                [
                    py,
                    "scripts/run_hangul_curated_ingest_pilot_v1.py",
                    "--manifest",
                    V2_MANIFEST,
                    "--overlay-path",
                    str(CANDIDATE.relative_to(ROOT)).replace("\\", "/"),
                    "--base-lexicon",
                    PROD,
                    "--skip-rebuild-overlay",
                    "--out-json",
                    "reports/lexicon_hangul_curated_pilot_v3_track_a_merge_preflight_latest.json",
                ],
            )
        )

    steps.extend(
        [
            ("preflight_packet", [py, "scripts/build_hangul_v3_track_a_merge_preflight_packet_v1.py"]),
            (
                "preflight_gate",
                [py, "scripts/check_hangul_v3_track_a_merge_preflight_gate_v1.py"]
                + (["--enforce"] if args.enforce_gate else []),
            ),
        ]
    )

    report: dict[str, object] = {"schema": "hangul_v3_track_a_merge_preflight_chain_v1", "steps": {}, "ok": True}
    for name, cmd in steps:
        rc = _run(cmd)
        report["steps"][name] = {"exit_code": rc}
        if rc != 0 and rc != 2:
            report["ok"] = False
            print(json.dumps({"FAIL": name, "exit_code": rc}, ensure_ascii=False))
            return rc
        if name == "preflight_packet" and rc == 2:
            report["steps"][name]["note"] = "preflight_ready=false"
        if name == "preflight_gate" and args.enforce_gate and rc != 0:
            report["ok"] = False
            return rc

    out = ROOT / "reports/hangul_v3_track_a_merge_preflight_chain_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"OK": "hangul_v3_track_a_merge_preflight_chain complete", "profile": args.profile}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
