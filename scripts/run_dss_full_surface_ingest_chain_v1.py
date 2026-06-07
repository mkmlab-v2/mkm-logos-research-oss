#!/usr/bin/env python3
"""One-click FULL_SURFACE_CHUNK ingest chain (B-track · no apocrypha re-fetch)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT), check=False).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chunk-size", type=int, default=250)
    ap.add_argument("--max-surface-rows-per-file", type=int, default=120)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--skip-ab", action="store_true")
    args = ap.parse_args()

    ndjson_out = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_full_surface_latest.jsonl"
    merge_target = ROOT / "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"
    research_ndjson_ssot = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl"

    steps: list[tuple[str, list[str]]] = [
        ("authority_pin_policy", [sys.executable, "scripts/build_dss_authority_pin_policy_v1.py"]),
        (
            "apocrypha_research_context",
            [sys.executable, "scripts/ingest_dss_apocrypha_research_context_v1.py"],
        ),
        (
            "ndjson_full_surface_ingest",
            [
                sys.executable,
                "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py",
                "--ingest-mode",
                "full_surface_chunk",
                "--chunk-size",
                str(args.chunk_size),
                "--max-surface-rows-per-file",
                str(args.max_surface_rows_per_file),
                "--output-jsonl",
                str(ndjson_out),
                "--merge-into",
                str(merge_target),
            ],
        ),
        (
            "refresh_research_slice",
            [
                sys.executable,
                "scripts/refresh_biblical_history_news_observation_slice_v1.py",
                "--run-resonance-eval",
                "--lookback-days",
                str(args.lookback_days),
            ],
        ),
        (
            "full_surface_report",
            [sys.executable, "scripts/build_dss_full_surface_ingest_report_v1.py"],
        ),
    ]
    if not args.skip_ab:
        steps.extend(
            [
                (
                    "sync_ndjson_ssot_for_ab",
                    [
                        sys.executable,
                        "scripts/sync_dss_ndjson_research_context_from_full_surface_v1.py",
                    ],
                ),
                (
                    "biblical_resonance_production_ab",
                    [sys.executable, "scripts/build_biblical_resonance_research_production_ab_v1.py"],
                ),
                (
                    "dss_ndjson_resonance_uplift",
                    [sys.executable, "scripts/build_dss_ndjson_resonance_uplift_report_v1.py"],
                ),
            ]
        )

    log: list[dict[str, object]] = []
    for name, cmd in steps:
        rc = _run(cmd)
        log.append({"step": name, "return_code": rc})
        if rc != 0:
            print(json.dumps({"ok": False, "failed_step": name, "log": log}, ensure_ascii=False), file=sys.stderr)
            return rc

    out = ROOT / "reports/dss_full_surface_ingest_chain_latest.json"
    payload = {
        "schema": "dss_full_surface_ingest_chain_v1",
        "ok": True,
        "steps": log,
        "artifacts": {
            "ndjson_full_surface": str(ndjson_out),
            "merge_target": str(merge_target),
            "full_surface_report": "reports/dss_full_surface_ingest_report_latest.json",
            "ab": "reports/biblical_resonance_research_production_ab_latest.json",
            "uplift": "reports/dss_ndjson_resonance_uplift_latest.json",
        },
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "track_a_promotion": "blocked",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
