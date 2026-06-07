#!/usr/bin/env python3
"""Compare MANIFEST_SUMMARY vs FULL_SURFACE_CHUNK ingest outcomes (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FULL = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_full_surface_latest.jsonl"
DEFAULT_AUTH = ROOT / "projects/dss-4d-ingest/outputs/authority_readiness_command_center_followup_20260327_h_ext3.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/dss_tokens_research_smoke_v1.ndjson"
DEFAULT_OUT = ROOT / "reports/dss_full_surface_ingest_report_latest.json"
INGEST_SCRIPT = ROOT / "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ingest(
    *,
    mode: str,
    out_path: Path,
    chunk_size: int,
    ndjson_path: Path | None = None,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(INGEST_SCRIPT),
        "--authority-json",
        str(DEFAULT_AUTH),
        "--ingest-mode",
        mode,
        "--output-jsonl",
        str(out_path),
    ]
    if mode == "full_surface_chunk":
        cmd.extend(["--chunk-size", str(chunk_size), "--max-surface-rows-per-file", "50"])
    if ndjson_path is not None:
        cmd.extend(["--ndjson-path", str(ndjson_path)])
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"ingest failed: {mode}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full-surface-jsonl", type=Path, default=DEFAULT_FULL)
    ap.add_argument("--chunk-size", type=int, default=250)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    full_rows = 0
    if args.full_surface_jsonl.is_file():
        full_rows = sum(1 for line in args.full_surface_jsonl.read_text(encoding="utf-8").splitlines() if line.strip())

    with tempfile.TemporaryDirectory(prefix="dss_surface_cmp_") as tmp:
        manifest_out = Path(tmp) / "manifest.jsonl"
        surface_out = Path(tmp) / "surface.jsonl"
        manifest_meta = _run_ingest(mode="manifest_summary", out_path=manifest_out, chunk_size=args.chunk_size)
        surface_meta = _run_ingest(
            mode="full_surface_chunk",
            out_path=surface_out,
            chunk_size=2,
            ndjson_path=DEFAULT_FIXTURE,
        )

    payload = {
        "schema": "dss_full_surface_ingest_report_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "comparison": {
            "manifest_summary_fixture": manifest_meta,
            "full_surface_chunk_fixture_chunk_size_2": surface_meta,
            "row_multiplier_fixture": round(
                (surface_meta.get("row_count", 0) or 0) / max(1, manifest_meta.get("row_count", 1)),
                3,
            ),
        },
        "production_full_surface": {
            "path": str(args.full_surface_jsonl),
            "row_count": full_rows,
            "ingest_mode": "FULL_SURFACE_CHUNK",
            "chunk_size": args.chunk_size,
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "Full surface expands metadata rows per work chunk; no raw token text in canonical_text.",
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "full_surface_rows": full_rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
