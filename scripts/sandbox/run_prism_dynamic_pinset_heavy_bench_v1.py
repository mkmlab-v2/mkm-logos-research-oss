#!/usr/bin/env python3
"""[HYPO] Lane B phase-2: dynamic vs fixed pinset on heavy lanes only (meta channel)."""
from __future__ import annotations

import argparse
import json
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
DEFAULT_OUT = SANDBOX / "results" / "prism_dynamic_pinset_heavy_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [r.get(key) for r in rows if r.get(key) is not None]
    return sum(float(v) for v in vals) / len(vals) if vals else None


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
        "meta_channel_tokens": m.get("meta_channel_tokens"),
    }


def run_bench(
    input_path: Path,
    hardening_path: Path,
    *,
    dry_run: bool,
    max_cases: int,
) -> dict[str, Any]:
    from scripts.sandbox.bench_case_lib_v1 import HEAVY_LANES, filter_cases, load_cases
    from scripts.sandbox.build_prism_pinset_swap_v1 import format_pinset_block, select_pinset
    from scripts.sandbox.eval_proxy_with_meta_channel_v1 import eval_proxy_with_attachment, load_guarded_context

    all_cases = load_cases(input_path)
    cases_in = filter_cases(all_cases, lanes=HEAVY_LANES, max_cases=max_cases)

    if dry_run:
        return {
            "schema": "prism_dynamic_pinset_heavy_bench_v1",
            "lane": "B2_dynamic_pinset_heavy_meta",
            "generated_at_utc": _utc(),
            "research_only": True,
            "dry_run": True,
            "heavy_lanes": sorted(HEAVY_LANES),
            "case_count": len(cases_in),
        }

    profile, lane_intensity = load_guarded_context(hardening_path)
    contract = SANDBOX / "prism_pinset_swap_contract_v1.json"
    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"

    rows: list[dict[str, Any]] = []
    dynamic_sets: list[frozenset[str]] = []

    for item in cases_in:
        raw = str(item["raw_text"])
        lane_s = str(item.get("lane")) if item.get("lane") else None

        fixed = select_pinset(
            registry_path=registry,
            contract_path=contract,
            task_profile="py_coding",
            selection_mode="fixed_preferred",
        )
        dynamic = select_pinset(
            registry_path=registry,
            contract_path=contract,
            task_profile="py_coding_dynamic",
            context_text=raw,
            file_hint=lane_s or "",
            selection_mode="context_scored",
        )
        fixed_ids = frozenset(str(e.get("id")) for e in fixed.get("entries") or [])
        dynamic_ids = frozenset(str(e.get("id")) for e in dynamic.get("entries") or [])
        dynamic_sets.append(dynamic_ids)

        meta_fixed = eval_proxy_with_attachment(
            raw,
            profile,
            lane=lane_s,
            lane_intensity=lane_intensity,
            attachment_block=format_pinset_block(fixed),
            injection_mode="meta_channel_post_gatekeeper",
        )
        meta_dynamic = eval_proxy_with_attachment(
            raw,
            profile,
            lane=lane_s,
            lane_intensity=lane_intensity,
            attachment_block=format_pinset_block(dynamic),
            injection_mode="meta_channel_post_gatekeeper",
        )

        rows.append(
            {
                "id": item.get("id"),
                "lane": item.get("lane"),
                "fixed_pinset_ids": sorted(fixed_ids),
                "dynamic_pinset_ids": sorted(dynamic_ids),
                "pinset_ids_differ": fixed_ids != dynamic_ids,
                "meta_fixed": _slim(meta_fixed),
                "meta_dynamic": _slim(meta_dynamic),
            }
        )

    differ_count = sum(1 for r in rows if r.get("pinset_ids_differ"))
    unique_sets = len(set(dynamic_sets))

    return {
        "schema": "prism_dynamic_pinset_heavy_bench_v1",
        "lane": "B2_dynamic_pinset_heavy_meta",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "injection_mode": "meta_channel_post_gatekeeper",
        "heavy_lanes": sorted(HEAVY_LANES),
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "aggregate": {
            "pinset_ids_differ_count": differ_count,
            "dynamic_pinset_unique_sets": unique_sets,
            "dynamic_advantage_proven": unique_sets > 1 or differ_count > 0,
            "meta_fixed_avg_jaccard": _avg([r["meta_fixed"] for r in rows], "reconstruction_fidelity_jaccard"),
            "meta_dynamic_avg_jaccard": _avg([r["meta_dynamic"] for r in rows], "reconstruction_fidelity_jaccard"),
        },
        "cases": rows,
        "boundary_ack": "Heavy slice only; B-track.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Dynamic pinset heavy-lane bench (B2).")
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
        print(
            f"heavy={doc.get('case_count')} differ={agg.get('pinset_ids_differ_count')} "
            f"unique={agg.get('dynamic_pinset_unique_sets')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
