#!/usr/bin/env python3
"""[HYPO] Bootstrap Human Gate drop zone: data/rq025/intake/ for upstream λ CSV."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTAKE_DIR = ROOT / "data/rq025/intake"
EXAMPLE_META = ROOT / "docs/final/artifacts/fixtures/rq025_upstream_lambda_certified_sidecar_v1.example.meta.json"
DEFAULT_MANIFEST = INTAKE_DIR / "rq025_upstream_intake_manifest_v1.json"
DEFAULT_OUT = ROOT / "reports/rq025_upstream_intake_bootstrap_v1_latest.json"
SCHEMA = "rq025_upstream_intake_bootstrap_v1"
CANONICAL_CSV = INTAKE_DIR / "upstream_lambda_certified.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    example_meta_dst = INTAKE_DIR / "upstream_lambda_certified.csv.meta.json.example"
    if EXAMPLE_META.is_file():
        shutil.copy2(EXAMPLE_META, example_meta_dst)

    manifest: dict[str, Any] = {
        "schema": "rq025_upstream_intake_manifest_v1",
        "version": "1.0.0",
        "human_gate": True,
        "drop_zone_dir": str(INTAKE_DIR.relative_to(ROOT)).replace("\\", "/"),
        "canonical_files": {
            "csv": "upstream_lambda_certified.csv",
            "meta": "upstream_lambda_certified.csv.meta.json",
        },
        "example_meta": str(example_meta_dst.relative_to(ROOT)).replace("\\", "/")
        if example_meta_dst.is_file()
        else None,
        "commands_after_drop": [
            "py scripts/validate_rq025_upstream_lambda_csv_v1.py data/rq025/intake/upstream_lambda_certified.csv",
            "py scripts/run_rq025_oracle_meeting_chain_v1.py",
        ],
    }
    DEFAULT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_present = CANONICAL_CSV.is_file()
    meta_present = (INTAKE_DIR / "upstream_lambda_certified.csv.meta.json").is_file()

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "intake_dir": str(INTAKE_DIR.relative_to(ROOT)).replace("\\", "/"),
        "manifest": str(DEFAULT_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "canonical_csv_present": csv_present,
        "canonical_meta_present": meta_present,
        "ready_for_meeting_chain": csv_present and meta_present,
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out} intake={INTAKE_DIR} csv={csv_present} meta={meta_present} "
        f"ready={csv_present and meta_present}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
