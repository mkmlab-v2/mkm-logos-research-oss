#!/usr/bin/env python3
"""Sweep max_surface_rows_per_file for FULL_SURFACE_CHUNK ingest (B-track · metadata only)."""

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
DEFAULT_OUT = ROOT / "reports/dss_full_surface_cap_sweep_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ingest(*, cap: int, chunk_size: int, tmp_out: Path) -> dict[str, Any]:
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
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {"cap": cap, "ok": False, "error": (proc.stderr or proc.stdout or "")[-500:]}
    meta = json.loads(proc.stdout.strip().splitlines()[-1])
    meta["cap"] = cap
    meta["ok"] = True
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--caps", default="600,1200,2000,4000")
    ap.add_argument("--chunk-size", type=int, default=50)
    ap.add_argument("--apply-best", action="store_true", help="Re-run full surface ingest chain with best cap.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    caps = [int(x.strip()) for x in args.caps.split(",") if x.strip()]
    results: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for cap in caps:
        tmp = ROOT / "reports" / f"tmp_dss_surface_cap_{cap}.jsonl"
        row = _run_ingest(cap=cap, chunk_size=args.chunk_size, tmp_out=tmp)
        results.append(row)
        if row.get("ok") and (best is None or int(row.get("row_count") or 0) > int(best.get("row_count") or 0)):
            best = row

    payload = {
        "schema": "dss_full_surface_cap_sweep_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "chunk_size": args.chunk_size,
        "results": results,
        "best_cap": best.get("cap") if best else None,
        "best_row_count": best.get("row_count") if best else None,
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "Higher cap increases metadata chunk rows; does not ingest raw token text.",
        },
        "track_a_promotion": "blocked",
    }
    chain_ok = None
    if args.apply_best and best and best.get("cap"):
        chain_cmd = [
            sys.executable,
            str(ROOT / "scripts/run_dss_full_surface_ingest_chain_v1.py"),
            "--chunk-size",
            str(args.chunk_size),
            "--max-surface-rows-per-file",
            str(best["cap"]),
        ]
        chain_ok = subprocess.run(chain_cmd, cwd=str(ROOT), check=False).returncode == 0

    payload["applied_best"] = bool(args.apply_best and best)
    payload["full_chain_ok"] = chain_ok

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "best_cap": payload["best_cap"], "best_row_count": payload["best_row_count"], "full_chain_ok": chain_ok},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
