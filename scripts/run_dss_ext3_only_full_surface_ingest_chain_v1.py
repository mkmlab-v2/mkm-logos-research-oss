#!/usr/bin/env python3
"""FULL_SURFACE_CHUNK ingest using ext3 Hebrew-priority + DSS smoke only (no ext2 leg)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT3_NDJSON = [
    "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson",
    "projects/dss-4d-ingest/outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson",
]
DEFAULT_SURFACE = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_ext3_only_full_surface_latest.jsonl"
DEFAULT_SSOT = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_ext3_only_research_context_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/dss_ext3_only_full_surface_ingest_chain_latest.json"


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT), check=False).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chunk-size", type=int, default=50)
    ap.add_argument("--max-surface-rows-per-file", type=int, default=1200)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--skip-ab", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ingest_cmd = [
        sys.executable,
        "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py",
        "--ingest-mode",
        "full_surface_chunk",
        "--chunk-size",
        str(args.chunk_size),
        "--max-surface-rows-per-file",
        str(args.max_surface_rows_per_file),
        "--output-jsonl",
        str(DEFAULT_SURFACE),
    ]
    for rel in EXT3_NDJSON:
        ingest_cmd.extend(["--ndjson-path", rel])

    steps: list[tuple[str, list[str]]] = [
        (
            "production_news_refresh_if_thin",
            [sys.executable, "scripts/refresh_biblical_history_production_news_v1.py", "--lookback-days", str(args.lookback_days)],
        ),
        ("authority_pin_policy", [sys.executable, "scripts/build_dss_authority_pin_policy_v1.py"]),
        ("apocrypha_research_context", [sys.executable, "scripts/ingest_dss_apocrypha_research_context_v1.py"]),
        ("ndjson_ext3_only_surface_ingest", ingest_cmd),
        (
            "sync_ext3_only_ssot",
            [
                sys.executable,
                "-c",
                (
                    "import shutil, pathlib; "
                    f"src=pathlib.Path(r'{DEFAULT_SURFACE}'); "
                    f"dst=pathlib.Path(r'{DEFAULT_SSOT}'); "
                    "dst.parent.mkdir(parents=True, exist_ok=True); "
                    "shutil.copy2(src, dst); "
                    "print('ok')"
                ),
            ],
        ),
    ]
    if not args.skip_ab:
        steps.append(
            (
                "isolated_production_ab_ext3_only",
                [
                    sys.executable,
                    "scripts/build_biblical_resonance_isolated_production_ab_v1.py",
                    "--ndjson-context-jsonl",
                    str(DEFAULT_SSOT),
                    "--output-json",
                    "reports/biblical_resonance_isolated_production_ab_ext3_only_latest.json",
                ],
            )
        )

    log: list[dict[str, object]] = []
    for name, cmd in steps:
        rc = _run(cmd)
        log.append({"step": name, "return_code": rc})
        if rc != 0:
            print(json.dumps({"ok": False, "failed_step": name, "log": log}, ensure_ascii=False), file=sys.stderr)
            return rc

    surface_rows = sum(1 for ln in DEFAULT_SURFACE.read_text(encoding="utf-8").splitlines() if ln.strip()) if DEFAULT_SURFACE.is_file() else 0
    payload = {
        "schema": "dss_ext3_only_full_surface_ingest_chain_v1",
        "ok": True,
        "steps": log,
        "ndjson_profile": "ext3_only",
        "ndjson_files": EXT3_NDJSON,
        "surface_rows": surface_rows,
        "artifacts": {
            "full_surface": str(DEFAULT_SURFACE),
            "research_context": str(DEFAULT_SSOT),
            "isolated_ab": "reports/biblical_resonance_isolated_production_ab_ext3_only_latest.json",
        },
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "track_a_promotion": "blocked",
    }
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "surface_rows": surface_rows, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
