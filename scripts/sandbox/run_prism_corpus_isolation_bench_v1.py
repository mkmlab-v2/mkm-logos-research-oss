#!/usr/bin/env python3
"""[HYPO] Lane E: isolate corpus vs meta effects on no-guard (4 arms)."""
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
DEFAULT_OUT = SANDBOX / "results" / "prism_corpus_isolation_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
    }


def run_bench(
    input_path: Path,
    no_guard_profile: Path,
    *,
    dry_run: bool,
    max_cases: int,
    corpus_max_files: int,
    corpus_max_terms: int,
) -> dict[str, Any]:
    from scripts.sandbox.bench_case_lib_v1 import load_cases
    from scripts.sandbox.build_prism_pinset_swap_v1 import format_pinset_block, select_pinset
    from scripts.sandbox.eval_no_guard_with_meta_channel_v1 import eval_no_guard_with_attachment
    from scripts.sandbox.run_no_guard_limit_stress_test_v1 import _harvest_repo_must_keep

    cases_in = load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "prism_corpus_isolation_bench_v1",
            "lane": "E_corpus_meta_isolation",
            "dry_run": True,
            "case_count": len(cases_in),
        }

    must_keep_extra, corpus_meta = _harvest_repo_must_keep(
        max_files=corpus_max_files,
        max_terms=corpus_max_terms,
    )
    contract = SANDBOX / "prism_pinset_swap_contract_v1.json"
    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"
    pinset_block = format_pinset_block(
        select_pinset(
            registry_path=registry,
            contract_path=contract,
            task_profile="py_coding",
            selection_mode="fixed_preferred",
        )
    )

    rows: list[dict[str, Any]] = []
    for item in cases_in:
        raw = str(item["raw_text"])
        lane_s = str(item.get("lane")) if item.get("lane") else None

        baseline = eval_no_guard_with_attachment(
            raw, no_guard_profile=no_guard_profile, lane=lane_s, injection_mode="none"
        )
        corpus_only = eval_no_guard_with_attachment(
            raw,
            no_guard_profile=no_guard_profile,
            lane=lane_s,
            injection_mode="none",
            must_keep_extra=must_keep_extra,
        )
        meta_only = eval_no_guard_with_attachment(
            raw,
            no_guard_profile=no_guard_profile,
            lane=lane_s,
            attachment_block=pinset_block,
            injection_mode="meta_channel_post_gatekeeper",
        )
        meta_corpus = eval_no_guard_with_attachment(
            raw,
            no_guard_profile=no_guard_profile,
            lane=lane_s,
            attachment_block=pinset_block,
            injection_mode="meta_channel_post_gatekeeper",
            must_keep_extra=must_keep_extra,
        )

        b_j = baseline.get("reconstruction_fidelity_jaccard")
        rows.append(
            {
                "id": item.get("id"),
                "lane": item.get("lane"),
                "baseline": _slim(baseline),
                "corpus_only": _slim(corpus_only),
                "meta_only": _slim(meta_only),
                "meta_corpus": _slim(meta_corpus),
                "corpus_only_delta_jaccard": (
                    float(corpus_only.get("reconstruction_fidelity_jaccard") or 0) - float(b_j or 0)
                    if b_j is not None and corpus_only.get("reconstruction_fidelity_jaccard") is not None
                    else None
                ),
                "meta_only_preserves": b_j == meta_only.get("reconstruction_fidelity_jaccard"),
            }
        )

    def _avg(key: str, arm: str) -> float | None:
        vals = [r[arm].get(key) for r in rows if r.get(arm, {}).get(key) is not None]
        return sum(float(v) for v in vals) / len(vals) if vals else None

    return {
        "schema": "prism_corpus_isolation_bench_v1",
        "lane": "E_corpus_meta_isolation",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "case_count": len(rows),
        "corpus_expansion": {**corpus_meta, "must_keep_extra_count": len(must_keep_extra)},
        "aggregate": {
            "baseline_avg_jaccard": _avg("reconstruction_fidelity_jaccard", "baseline"),
            "corpus_only_avg_jaccard": _avg("reconstruction_fidelity_jaccard", "corpus_only"),
            "meta_only_avg_jaccard": _avg("reconstruction_fidelity_jaccard", "meta_only"),
            "meta_corpus_avg_jaccard": _avg("reconstruction_fidelity_jaccard", "meta_corpus"),
            "meta_only_preserves_count": sum(1 for r in rows if r.get("meta_only_preserves")),
            "corpus_only_changed_count": sum(
                1 for r in rows if abs(r.get("corpus_only_delta_jaccard") or 0) > 0.01
            ),
        },
        "interpretation_ko": {
            "corpus_only": "must_keep bloat만 — meta 없음",
            "meta_only": "sidecar만 — must_keep 기본",
            "isolation": "corpus 효과와 meta 효과 분리",
        },
        "cases": rows,
        "boundary_ack": "Simulated must_keep only.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Corpus vs meta isolation bench (E).")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--no-guard-profile", default=str(DEFAULT_NO_GUARD))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--corpus-max-files", type=int, default=120)
    ap.add_argument("--corpus-max-terms", type=int, default=5000)
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
        corpus_max_files=max(0, int(args.corpus_max_files)),
        corpus_max_terms=max(0, int(args.corpus_max_terms)),
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
            f"b={agg.get('baseline_avg_jaccard')} corp={agg.get('corpus_only_avg_jaccard')} "
            f"meta={agg.get('meta_only_avg_jaccard')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
