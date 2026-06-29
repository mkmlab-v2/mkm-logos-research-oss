#!/usr/bin/env python3
"""[HYPO] Lane A: baseline vs prepend vs post-gatekeeper meta channel (n=20)."""
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
DEFAULT_OUT = SANDBOX / "results" / "prism_meta_channel_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("raw_text") is not None:
            rows.append(row)
    return rows


def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [r.get(key) for r in rows if r.get(key) is not None]
    return sum(float(v) for v in vals) / len(vals) if vals else None


def run_bench(
    input_path: Path,
    hardening_path: Path,
    *,
    dry_run: bool,
    max_cases: int,
) -> dict[str, Any]:
    from scripts.sandbox.build_prism_pinset_swap_v1 import format_pinset_block, select_pinset
    from scripts.sandbox.eval_proxy_with_meta_channel_v1 import eval_proxy_with_attachment, load_guarded_context

    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "prism_meta_channel_bench_v1",
            "lane": "A_post_gatekeeper_meta",
            "generated_at_utc": _utc(),
            "research_only": True,
            "dry_run": True,
            "case_count": len(cases_in),
        }

    profile, lane_intensity = load_guarded_context(hardening_path)
    contract = SANDBOX / "prism_pinset_swap_contract_v1.json"
    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"

    fixed_pinset = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile="py_coding",
        selection_mode="fixed_preferred",
    )
    pinset_block = format_pinset_block(fixed_pinset)

    rows: list[dict[str, Any]] = []
    for item in cases_in:
        raw = str(item["raw_text"])
        lane = str(item.get("lane")) if item.get("lane") else None

        baseline = eval_proxy_with_attachment(
            raw,
            profile,
            lane=lane,
            lane_intensity=lane_intensity,
            injection_mode="none",
        )
        prepend = eval_proxy_with_attachment(
            raw,
            profile,
            lane=lane,
            lane_intensity=lane_intensity,
            attachment_block=pinset_block,
            injection_mode="prepend",
        )
        meta = eval_proxy_with_attachment(
            raw,
            profile,
            lane=lane,
            lane_intensity=lane_intensity,
            attachment_block=pinset_block,
            injection_mode="meta_channel_post_gatekeeper",
        )

        rows.append(
            {
                "id": item.get("id"),
                "lane": item.get("lane"),
                "baseline": _slim(baseline),
                "prepend_fixed_pinset": _slim(prepend),
                "meta_channel_fixed_pinset": _slim(meta),
                "meta_preserves_baseline_jaccard": (
                    baseline.get("reconstruction_fidelity_jaccard")
                    == meta.get("reconstruction_fidelity_jaccard")
                    and baseline.get("proxy_path") == meta.get("proxy_path")
                ),
            }
        )

    base_rows = [r["baseline"] for r in rows]
    prep_rows = [r["prepend_fixed_pinset"] for r in rows]
    meta_rows = [r["meta_channel_fixed_pinset"] for r in rows]

    return {
        "schema": "prism_meta_channel_bench_v1",
        "lane": "A_post_gatekeeper_meta",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "contract": "experiments/no_guard_limit_test/prism_meta_channel_contract_v1.json",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "fixed_pinset_ids": [e.get("id") for e in fixed_pinset.get("entries") or []],
        "aggregate": {
            "baseline_avg_jaccard": _avg(base_rows, "reconstruction_fidelity_jaccard"),
            "prepend_avg_jaccard": _avg(prep_rows, "reconstruction_fidelity_jaccard"),
            "meta_channel_avg_jaccard": _avg(meta_rows, "reconstruction_fidelity_jaccard"),
            "baseline_gatekeeper_bypass_count": sum(
                1 for r in base_rows if r.get("proxy_path") == "gatekeeper_bypass"
            ),
            "prepend_gatekeeper_bypass_count": sum(
                1 for r in prep_rows if r.get("proxy_path") == "gatekeeper_bypass"
            ),
            "meta_gatekeeper_bypass_count": sum(
                1 for r in meta_rows if r.get("proxy_path") == "gatekeeper_bypass"
            ),
            "meta_preserves_baseline_count": sum(1 for r in rows if r.get("meta_preserves_baseline_jaccard")),
            "avg_meta_channel_tokens": _avg(meta_rows, "meta_channel_tokens"),
        },
        "cases": rows,
        "interpretation_ko": {
            "success": "meta_channel Jaccard/proxy_path = baseline + meta tokens only",
            "prepend_regression": "prepend가 bypass를 깨면 aggregate prepend Jaccard 하락",
        },
        "boundary_ack": "B-track; user-text fidelity only.",
    }


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
        "injection_mode": m.get("injection_mode"),
        "gatekeeper_input_tokens": m.get("gatekeeper_input_tokens"),
        "meta_channel_tokens": m.get("meta_channel_tokens"),
        "effective_context_tokens": m.get("effective_context_tokens"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prism meta channel bench lane A.")
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
            f"b_jac={agg.get('baseline_avg_jaccard')} "
            f"prep_jac={agg.get('prepend_avg_jaccard')} "
            f"meta_jac={agg.get('meta_channel_avg_jaccard')} "
            f"preserve={agg.get('meta_preserves_baseline_count')}/{doc.get('case_count')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
