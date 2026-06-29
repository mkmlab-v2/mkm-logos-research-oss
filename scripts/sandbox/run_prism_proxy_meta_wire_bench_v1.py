#!/usr/bin/env python3
"""[HYPO] Bench: coding_proxy_compress_surface meta wire (env flag off vs on)."""
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
DEFAULT_OUT = SANDBOX / "results" / "prism_proxy_meta_wire_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_bench(
    input_path: Path,
    hardening_path: Path,
    *,
    dry_run: bool,
    max_cases: int,
) -> dict[str, Any]:
    from scripts.sandbox.bench_case_lib_v1 import load_cases
    from scripts.run_cursor_coding_compress_bench_v1 import _load_lane_intensity, _selected_profile

    cases_in = load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "prism_proxy_meta_wire_bench_v1",
            "dry_run": True,
            "case_count": len(cases_in),
        }

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path)

    from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface

    rows: list[dict[str, Any]] = []
    for item in cases_in:
        raw = str(item["raw_text"])
        lane_s = str(item.get("lane")) if item.get("lane") else None

        os.environ.pop("MKM_PRISM_META_CHANNEL_BTRACK", None)
        off = coding_proxy_compress_surface(
            raw, profile, lane=lane_s, lane_intensity=lane_intensity
        )

        os.environ["MKM_PRISM_META_CHANNEL_BTRACK"] = "1"
        on = coding_proxy_compress_surface(
            raw, profile, lane=lane_s, lane_intensity=lane_intensity
        )
        os.environ.pop("MKM_PRISM_META_CHANNEL_BTRACK", None)

        rows.append(
            {
                "id": item.get("id"),
                "lane": item.get("lane"),
                "flag_off_jaccard": off.get("reconstruction_fidelity_jaccard"),
                "flag_on_jaccard": on.get("reconstruction_fidelity_jaccard"),
                "flag_off_proxy_path": off.get("proxy_path"),
                "flag_on_proxy_path": on.get("proxy_path"),
                "meta_present_on": on.get("meta_channel") is not None,
                "meta_tokens_on": (on.get("meta_channel") or {}).get("meta_channel_tokens"),
                "preserves_metrics": (
                    off.get("reconstruction_fidelity_jaccard")
                    == on.get("reconstruction_fidelity_jaccard")
                    and off.get("proxy_path") == on.get("proxy_path")
                ),
            }
        )

    preserve = sum(1 for r in rows if r.get("preserves_metrics"))
    meta_ok = sum(1 for r in rows if r.get("meta_present_on"))

    return {
        "schema": "prism_proxy_meta_wire_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "env_flag": "MKM_PRISM_META_CHANNEL_BTRACK",
        "wiring": "scripts/core/coding_proxy_compress_v1.py::_maybe_attach_meta_sidecar",
        "case_count": len(rows),
        "aggregate": {
            "preserves_metrics_count": preserve,
            "meta_present_count": meta_ok,
            "wire_poc_pass": preserve == len(rows) and meta_ok == len(rows),
        },
        "cases": rows,
        "boundary_ack": "Default env off; B-track only.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Proxy meta wire bench.")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--hardening-config", default=str(DEFAULT_HARDENING))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cases", type=int, default=0)
    args = ap.parse_args()

    input_path = Path(args.input_jsonl)
    hardening_path = Path(args.hardening_config)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not hardening_path.is_absolute():
        hardening_path = ROOT / hardening_path

    doc = run_bench(
        input_path,
        hardening_path,
        dry_run=bool(args.dry_run),
        max_cases=max(0, int(args.max_cases)),
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    if not args.dry_run:
        agg = doc.get("aggregate") or {}
        print(f"wire_pass={agg.get('wire_poc_pass')} preserve={agg.get('preserves_metrics_count')}/{doc.get('case_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
