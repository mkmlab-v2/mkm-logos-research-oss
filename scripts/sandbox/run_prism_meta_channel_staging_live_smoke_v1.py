#!/usr/bin/env python3
"""[HYPO] Post-approval live smoke: coding_proxy with MKM_PRISM_META_CHANNEL_BTRACK=1."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SANDBOX = ROOT / "experiments" / "no_guard_limit_test"
DEFAULT_INPUT = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n20.jsonl"
DEFAULT_HARDENING = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"
DEFAULT_OUT = SANDBOX / "results" / "prism_meta_channel_staging_live_smoke_v1_latest.json"
ENV_FLAG = "MKM_PRISM_META_CHANNEL_BTRACK"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_smoke(
    input_path: Path,
    hardening_path: Path,
    *,
    max_cases: int,
    dry_run: bool,
) -> dict[str, Any]:
    from scripts.sandbox.bench_case_lib_v1 import load_cases
    from scripts.run_cursor_coding_compress_bench_v1 import _load_lane_intensity, _selected_profile

    cases = load_cases(input_path)
    if max_cases > 0:
        cases = cases[:max_cases]

    if dry_run:
        return {
            "schema": "prism_meta_channel_staging_live_smoke_v1",
            "dry_run": True,
            "case_count": len(cases),
            "env_flag": ENV_FLAG,
        }

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path)

    from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface

    rows: list[dict[str, Any]] = []
    os.environ[ENV_FLAG] = "1"
    try:
        for item in cases:
            raw = str(item["raw_text"])
            lane_s = str(item.get("lane")) if item.get("lane") else None
            out = coding_proxy_compress_surface(
                raw, profile, lane=lane_s, lane_intensity=lane_intensity
            )
            meta = out.get("meta_channel") or {}
            rows.append(
                {
                    "id": item.get("id"),
                    "lane": item.get("lane"),
                    "jaccard": out.get("reconstruction_fidelity_jaccard"),
                    "proxy_path": out.get("proxy_path"),
                    "meta_present": meta is not None and bool(meta),
                    "meta_tokens": meta.get("meta_channel_tokens") if isinstance(meta, dict) else None,
                    "effective_context_tokens": out.get("effective_context_tokens"),
                    "meta_research_only": out.get("meta_channel_research_only"),
                }
            )
    finally:
        os.environ.pop(ENV_FLAG, None)

    meta_ok = sum(1 for r in rows if r.get("meta_present"))
    smoke_pass = meta_ok == len(rows) and len(rows) > 0

    return {
        "schema": "prism_meta_channel_staging_live_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "env_flag": ENV_FLAG,
        "env_value": "1",
        "staging_live_smoke_pass": smoke_pass,
        "case_count": len(rows),
        "aggregate": {
            "meta_present_count": meta_ok,
            "avg_meta_tokens": (
                sum(float(r.get("meta_tokens") or 0) for r in rows) / len(rows) if rows else None
            ),
        },
        "cases": rows,
        "boundary_ack": "Live smoke with env ON; not production default; rollback unset env.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Staging live smoke with meta env ON.")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--hardening-config", default=str(DEFAULT_HARDENING))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--max-cases", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 unless staging_live_smoke_pass")
    args = ap.parse_args()

    input_path = Path(args.input_jsonl)
    hardening_path = Path(args.hardening_config)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not hardening_path.is_absolute():
        hardening_path = ROOT / hardening_path

    doc = run_smoke(
        input_path,
        hardening_path,
        max_cases=max(0, int(args.max_cases)),
        dry_run=bool(args.dry_run),
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    if not args.dry_run:
        print(f"staging_live_smoke_pass={doc.get('staging_live_smoke_pass')}")
    if args.strict and not doc.get("staging_live_smoke_pass") and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
