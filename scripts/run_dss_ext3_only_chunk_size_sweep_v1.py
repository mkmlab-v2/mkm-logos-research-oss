#!/usr/bin/env python3
"""Sweep chunk_size for ext3-only FULL_SURFACE_CHUNK profile (B-track · metadata only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "scripts/ingest_dss_ndjson_token_manifest_research_context_v1.py"
EXT3_NDJSON = [
    "projects/dss-4d-ingest/outputs/apocrypha_tokens_pilot_manifest_ext3_hebrew_priority.ndjson",
    "projects/dss-4d-ingest/outputs/dss_tokens_ci_smoke_manifest_tf4.ndjson",
]
DEFAULT_OUT = ROOT / "reports/dss_ext3_only_chunk_size_sweep_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ingest(*, chunk_size: int, cap: int, tmp_out: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(INGEST),
        "--ingest-mode",
        "full_surface_chunk",
        "--chunk-size",
        str(chunk_size),
        "--max-surface-rows-per-file",
        str(cap),
        "--output-jsonl",
        str(tmp_out),
    ]
    for rel in EXT3_NDJSON:
        cmd.extend(["--ndjson-path", rel])
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {"chunk_size": chunk_size, "ok": False, "error": (proc.stderr or proc.stdout or "")[-500:]}
    meta = json.loads(proc.stdout.strip().splitlines()[-1])
    meta["chunk_size"] = chunk_size
    meta["ok"] = True
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chunk-sizes", default="40,50,75,100")
    ap.add_argument("--max-surface-rows-per-file", type=int, default=1200)
    ap.add_argument("--apply-best", action="store_true")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sizes = [int(x.strip()) for x in args.chunk_sizes.split(",") if x.strip()]
    results: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for size in sizes:
        tmp = ROOT / "reports" / f"tmp_dss_ext3_surface_chunk_{size}.jsonl"
        row = _run_ingest(chunk_size=size, cap=args.max_surface_rows_per_file, tmp_out=tmp)
        results.append(row)
        if row.get("ok") and (best is None or int(row.get("row_count") or 0) > int(best.get("row_count") or 0)):
            best = row

    chain_ok = None
    if args.apply_best and best and best.get("chunk_size"):
        chain_cmd = [
            sys.executable,
            str(ROOT / "scripts/run_dss_ext3_only_full_surface_ingest_chain_v1.py"),
            "--chunk-size",
            str(best["chunk_size"]),
            "--max-surface-rows-per-file",
            str(args.max_surface_rows_per_file),
        ]
        chain_ok = subprocess.run(chain_cmd, cwd=str(ROOT), check=False).returncode == 0

    payload = {
        "schema": "dss_ext3_only_chunk_size_sweep_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "ndjson_profile": "ext3_only",
        "max_surface_rows_per_file": args.max_surface_rows_per_file,
        "results": results,
        "best_chunk_size": best.get("chunk_size") if best else None,
        "best_row_count": best.get("row_count") if best else None,
        "applied_best": bool(args.apply_best and best),
        "ext3_chain_ok": chain_ok,
        "track_a_promotion": "blocked",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "best_chunk_size": payload["best_chunk_size"], "best_row_count": payload["best_row_count"], "ext3_chain_ok": chain_ok},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
