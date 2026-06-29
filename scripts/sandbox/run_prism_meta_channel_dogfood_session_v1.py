#!/usr/bin/env python3
"""[HYPO] Dogfood session: meta env ON → sample compress → log → env OFF."""
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

DEFAULT_INPUT = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl"
DEFAULT_HARDENING = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"
DEFAULT_OUT = ROOT / "reports/dogfood_meta_channel_session_v1_latest.json"
ENV_FLAG = "MKM_PRISM_META_CHANNEL_BTRACK"
DEFAULT_SAMPLE_IDS = ("cc_n03", "cc_n10", "cc_n21", "cc_n23", "cc_n35")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_session(
    input_path: Path,
    hardening_path: Path,
    *,
    sample_ids: tuple[str, ...],
    dry_run: bool,
) -> dict[str, Any]:
    from scripts.sandbox.bench_case_lib_v1 import load_cases
    from scripts.run_cursor_coding_compress_bench_v1 import _load_lane_intensity, _selected_profile
    from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface

    all_cases = {str(c.get("id")): c for c in load_cases(input_path)}
    missing = [sid for sid in sample_ids if sid not in all_cases]
    if missing:
        raise SystemExit(f"missing sample ids: {missing}")

    if dry_run:
        return {
            "schema": "dogfood_meta_channel_session_v1",
            "dry_run": True,
            "sample_ids": list(sample_ids),
        }

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path)

    rows: list[dict[str, Any]] = []
    os.environ[ENV_FLAG] = "1"
    try:
        for sid in sample_ids:
            item = all_cases[sid]
            raw = str(item["raw_text"])
            lane_s = str(item.get("lane")) if item.get("lane") else None
            off_env = os.environ.pop(ENV_FLAG, None)
            off = coding_proxy_compress_surface(
                raw, profile, lane=lane_s, lane_intensity=lane_intensity
            )
            if off_env:
                os.environ[ENV_FLAG] = off_env
            on = coding_proxy_compress_surface(
                raw, profile, lane=lane_s, lane_intensity=lane_intensity
            )
            meta = on.get("meta_channel") or {}
            rows.append(
                {
                    "id": sid,
                    "lane": item.get("lane"),
                    "flag_off_jaccard": off.get("reconstruction_fidelity_jaccard"),
                    "flag_on_jaccard": on.get("reconstruction_fidelity_jaccard"),
                    "preserves_metrics": off.get("reconstruction_fidelity_jaccard")
                    == on.get("reconstruction_fidelity_jaccard"),
                    "meta_present": bool(meta),
                    "meta_tokens": meta.get("meta_channel_tokens") if isinstance(meta, dict) else None,
                    "effective_context_tokens": on.get("effective_context_tokens"),
                    "proxy_path": on.get("proxy_path"),
                }
            )
    finally:
        os.environ.pop(ENV_FLAG, None)

    preserve = sum(1 for r in rows if r.get("preserves_metrics"))
    meta_ok = sum(1 for r in rows if r.get("meta_present"))

    return {
        "schema": "dogfood_meta_channel_session_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "env_flag": ENV_FLAG,
        "env_session": "enabled_during_run_then_removed",
        "sample_ids": list(sample_ids),
        "session_pass": preserve == len(rows) and meta_ok == len(rows),
        "aggregate": {
            "preserves_metrics_count": preserve,
            "meta_present_count": meta_ok,
            "avg_meta_tokens": (
                sum(float(r.get("meta_tokens") or 0) for r in rows) / len(rows) if rows else None
            ),
        },
        "observations": rows,
        "boundary_ack": "Dogfood log only; not Track A promotion; default env remains OFF after run.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Dogfood meta channel session log.")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--hardening-config", default=str(DEFAULT_HARDENING))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--sample-id", action="append", dest="sample_ids")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    input_path = Path(args.input_jsonl)
    hardening_path = Path(args.hardening_config)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not hardening_path.is_absolute():
        hardening_path = ROOT / hardening_path

    ids = tuple(args.sample_ids) if args.sample_ids else DEFAULT_SAMPLE_IDS
    doc = run_session(
        input_path,
        hardening_path,
        sample_ids=ids,
        dry_run=bool(args.dry_run),
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    if not args.dry_run:
        print(f"session_pass={doc.get('session_pass')}")
    if args.strict and not doc.get("session_pass") and not args.dry_run:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
