#!/usr/bin/env python3
"""[HYPO] Lane C: No-Guard + fixed pinset (none vs prepend vs meta channel) n=20."""
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
DEFAULT_NO_GUARD = SANDBOX / "no_guard_profile_v1.json"
DEFAULT_OUT = SANDBOX / "results" / "prism_no_guard_meta_channel_bench_v1_latest.json"
GUARDED_META_REF = SANDBOX / "results" / "prism_meta_channel_bench_v1_latest.json"


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


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
        "scenario": m.get("scenario"),
        "injection_mode": m.get("injection_mode"),
        "compress_input_tokens": m.get("compress_input_tokens"),
        "meta_channel_tokens": m.get("meta_channel_tokens"),
        "effective_context_tokens": m.get("effective_context_tokens"),
    }


def _load_guarded_meta_reference() -> dict[str, Any] | None:
    if not GUARDED_META_REF.is_file():
        return None
    try:
        doc = json.loads(GUARDED_META_REF.read_text(encoding="utf-8"))
        agg = doc.get("aggregate") or {}
        return {
            "source": str(GUARDED_META_REF.relative_to(ROOT)).replace("\\", "/"),
            "baseline_avg_jaccard": agg.get("baseline_avg_jaccard"),
            "meta_channel_avg_jaccard": agg.get("meta_channel_avg_jaccard"),
            "meta_preserves_baseline_count": agg.get("meta_preserves_baseline_count"),
        }
    except (json.JSONDecodeError, OSError):
        return None


def run_bench(
    input_path: Path,
    no_guard_profile: Path,
    *,
    dry_run: bool,
    max_cases: int,
) -> dict[str, Any]:
    from scripts.sandbox.build_prism_pinset_swap_v1 import format_pinset_block, select_pinset
    from scripts.sandbox.eval_no_guard_with_meta_channel_v1 import eval_no_guard_with_attachment

    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "prism_no_guard_meta_channel_bench_v1",
            "lane": "C_no_guard_meta_channel",
            "generated_at_utc": _utc(),
            "research_only": True,
            "dry_run": True,
            "case_count": len(cases_in),
        }

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
        lane_s = str(item.get("lane")) if item.get("lane") else None

        baseline = eval_no_guard_with_attachment(
            raw,
            no_guard_profile=no_guard_profile,
            lane=lane_s,
            injection_mode="none",
        )
        prepend = eval_no_guard_with_attachment(
            raw,
            no_guard_profile=no_guard_profile,
            lane=lane_s,
            attachment_block=pinset_block,
            injection_mode="prepend",
        )
        meta = eval_no_guard_with_attachment(
            raw,
            no_guard_profile=no_guard_profile,
            lane=lane_s,
            attachment_block=pinset_block,
            injection_mode="meta_channel_post_gatekeeper",
        )

        rows.append(
            {
                "id": item.get("id"),
                "lane": item.get("lane"),
                "no_guard_baseline": _slim(baseline),
                "no_guard_prepend_pinset": _slim(prepend),
                "no_guard_meta_channel": _slim(meta),
                "meta_preserves_no_guard_jaccard": (
                    baseline.get("reconstruction_fidelity_jaccard")
                    == meta.get("reconstruction_fidelity_jaccard")
                    and baseline.get("proxy_path") == meta.get("proxy_path")
                ),
            }
        )

    base_rows = [r["no_guard_baseline"] for r in rows]
    prep_rows = [r["no_guard_prepend_pinset"] for r in rows]
    meta_rows = [r["no_guard_meta_channel"] for r in rows]

    return {
        "schema": "prism_no_guard_meta_channel_bench_v1",
        "lane": "C_no_guard_meta_channel",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "no_guard_profile": str(no_guard_profile.relative_to(ROOT)).replace("\\", "/"),
        "meta_channel_contract": "experiments/no_guard_limit_test/prism_meta_channel_contract_v1.json",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "fixed_pinset_ids": [e.get("id") for e in fixed_pinset.get("entries") or []],
        "aggregate": {
            "no_guard_baseline_avg_jaccard": _avg(base_rows, "reconstruction_fidelity_jaccard"),
            "no_guard_prepend_avg_jaccard": _avg(prep_rows, "reconstruction_fidelity_jaccard"),
            "no_guard_meta_avg_jaccard": _avg(meta_rows, "reconstruction_fidelity_jaccard"),
            "no_guard_baseline_min_jaccard": min(
                (r["reconstruction_fidelity_jaccard"] for r in base_rows if r.get("reconstruction_fidelity_jaccard") is not None),
                default=None,
            ),
            "no_guard_meta_min_jaccard": min(
                (r["reconstruction_fidelity_jaccard"] for r in meta_rows if r.get("reconstruction_fidelity_jaccard") is not None),
                default=None,
            ),
            "no_guard_baseline_avg_saving": _avg(base_rows, "token_saving_rate"),
            "no_guard_meta_avg_saving": _avg(meta_rows, "token_saving_rate"),
            "meta_preserves_no_guard_count": sum(1 for r in rows if r.get("meta_preserves_no_guard_jaccard")),
            "avg_meta_channel_tokens": _avg(meta_rows, "meta_channel_tokens"),
            "no_guard_avg_jaccard_below_075": (
                _avg(base_rows, "reconstruction_fidelity_jaccard") is not None
                and _avg(base_rows, "reconstruction_fidelity_jaccard") < 0.75
            ),
        },
        "guarded_meta_reference": _load_guarded_meta_reference(),
        "cases": rows,
        "interpretation_ko": {
            "no_guard": "gatekeeper·circuit breaker 없음 — 엔진 raw 한계 측정",
            "meta_success": "no_guard baseline과 meta Jaccard 동일 + sidecar 토큰만 추가",
            "prepend_risk": "pinset을 압축 입력에 합치면 saving↑ 품질↓ 가능",
        },
        "forbidden_claims": ["track_a_promotion", "production_sla", "unlimited_knowledge"],
        "boundary_ack": "Lane C only; mainline hardening untouched.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="No-Guard + Prism meta channel bench lane C.")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--no-guard-profile", default=str(DEFAULT_NO_GUARD))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cases", type=int, default=0)
    args = ap.parse_args()

    input_path = Path(args.input_jsonl)
    profile_path = Path(args.no_guard_profile)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not profile_path.is_absolute():
        profile_path = ROOT / profile_path

    doc = run_bench(
        input_path,
        profile_path,
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
            f"ng_b_jac={agg.get('no_guard_baseline_avg_jaccard')} "
            f"ng_meta_jac={agg.get('no_guard_meta_avg_jaccard')} "
            f"preserve={agg.get('meta_preserves_no_guard_count')}/{doc.get('case_count')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
