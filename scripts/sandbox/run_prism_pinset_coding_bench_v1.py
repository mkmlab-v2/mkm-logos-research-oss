#!/usr/bin/env python3
"""[HYPO] Bench: guarded coding proxy with vs without Prism pinset prepend (n=20)."""
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
DEFAULT_OUT = SANDBOX / "results" / "prism_pinset_coding_bench_v1_latest.json"


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


def _eval_guarded(text: str, *, lane: str | None, hardening_path: Path) -> dict[str, Any]:
    from scripts.run_cursor_coding_compress_bench_v1 import (
        _eval_proxy_aligned,
        _load_lane_intensity,
        _selected_profile,
    )

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path)
    m = _eval_proxy_aligned(text, profile, lane=lane, lane_intensity=lane_intensity)
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
    }


def run_bench(
    input_path: Path,
    hardening_path: Path,
    *,
    dry_run: bool,
    max_cases: int,
) -> dict[str, Any]:
    from scripts.sandbox.build_prism_pinset_swap_v1 import (
        estimate_pinset_tokens,
        format_pinset_block,
        select_pinset,
    )

    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    contract = SANDBOX / "prism_pinset_swap_contract_v1.json"
    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"

    if dry_run:
        return {
            "schema": "prism_pinset_coding_bench_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "dry_run": True,
            "case_count": len(cases_in),
            "boundary_ack": "Dry-run only.",
        }

    rows: list[dict[str, Any]] = []
    pinset_tokens_list: list[int] = []

    for item in cases_in:
        raw = str(item["raw_text"])
        lane = item.get("lane")
        lane_s = str(lane) if lane else None

        pinset = select_pinset(
            registry_path=registry,
            contract_path=contract,
            task_profile="py_coding",
            context_text=raw,
            file_hint=lane_s or "",
        )
        block = format_pinset_block(pinset)
        pin_tok = estimate_pinset_tokens(block)
        pinset_tokens_list.append(pin_tok)

        baseline = _eval_guarded(raw, lane=lane_s, hardening_path=hardening_path)
        with_pinset = _eval_guarded(block + raw, lane=lane_s, hardening_path=hardening_path)

        b_j = baseline.get("reconstruction_fidelity_jaccard")
        p_j = with_pinset.get("reconstruction_fidelity_jaccard")
        delta_j = None
        if b_j is not None and p_j is not None:
            delta_j = float(p_j) - float(b_j)

        rows.append(
            {
                "id": item.get("id"),
                "lane": lane,
                "pinset_entry_ids": [e.get("id") for e in pinset.get("entries") or []],
                "pinset_token_estimate": pin_tok,
                "baseline": baseline,
                "with_pinset": with_pinset,
                "delta_jaccard_with_pinset_minus_baseline": delta_j,
            }
        )

    b_jacs = [
        r["baseline"]["reconstruction_fidelity_jaccard"]
        for r in rows
        if r["baseline"].get("reconstruction_fidelity_jaccard") is not None
    ]
    p_jacs = [
        r["with_pinset"]["reconstruction_fidelity_jaccard"]
        for r in rows
        if r["with_pinset"].get("reconstruction_fidelity_jaccard") is not None
    ]
    avg_pinset_tok = sum(pinset_tokens_list) / len(pinset_tokens_list) if pinset_tokens_list else 0

    return {
        "schema": "prism_pinset_coding_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "hardening_config": str(hardening_path.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "aggregate": {
            "avg_pinset_token_estimate": avg_pinset_tok,
            "baseline_avg_jaccard": sum(b_jacs) / len(b_jacs) if b_jacs else None,
            "with_pinset_avg_jaccard": sum(p_jacs) / len(p_jacs) if p_jacs else None,
            "baseline_min_jaccard": min(b_jacs) if b_jacs else None,
            "with_pinset_min_jaccard": min(p_jacs) if p_jacs else None,
            "pinset_helps_jaccard_count": sum(
                1
                for r in rows
                if (r.get("delta_jaccard_with_pinset_minus_baseline") or 0) > 0.01
            ),
            "pinset_hurts_jaccard_count": sum(
                1
                for r in rows
                if (r.get("delta_jaccard_with_pinset_minus_baseline") or 0) < -0.01
            ),
        },
        "cases": rows,
        "interpretation_ko": {
            "pinset_role": "포인터 3개만 주입 — 전체 지식 사전 주입 아님",
            "success_signal": "with_pinset Jaccard 유지·개선 + pinset 토큰 상한 낮음",
        },
        "forbidden_claims": ["track_a_promotion", "unlimited_knowledge_injection"],
        "boundary_ack": "B-track bench; guarded proxy path only.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prism pinset coding bench (B-track).")
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
    if not input_path.is_file():
        raise SystemExit(f"missing input: {input_path}")

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
            f"pinset_tok~{agg.get('avg_pinset_token_estimate')} "
            f"b_jac={agg.get('baseline_avg_jaccard')} "
            f"p_jac={agg.get('with_pinset_avg_jaccard')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
