#!/usr/bin/env python3
"""[HYPO] Lane D: No-Guard + meta + corpus_expansion triple axis (n=20)."""
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
DEFAULT_OUT = SANDBOX / "results" / "prism_no_guard_meta_corpus_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    from scripts.sandbox.bench_case_lib_v1 import load_cases

    return load_cases(path)


def _avg(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [r.get(key) for r in rows if r.get(key) is not None]
    return sum(float(v) for v in vals) / len(vals) if vals else None


def _slim(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
        "scenario": m.get("scenario"),
        "meta_channel_tokens": m.get("meta_channel_tokens"),
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
    from scripts.sandbox.build_prism_pinset_swap_v1 import format_pinset_block, select_pinset
    from scripts.sandbox.eval_no_guard_with_meta_channel_v1 import eval_no_guard_with_attachment
    from scripts.sandbox.run_no_guard_limit_stress_test_v1 import _harvest_repo_must_keep

    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "prism_no_guard_meta_corpus_bench_v1",
            "lane": "D_no_guard_meta_corpus_triple",
            "generated_at_utc": _utc(),
            "research_only": True,
            "dry_run": True,
            "case_count": len(cases_in),
        }

    must_keep_extra, corpus_meta = _harvest_repo_must_keep(
        max_files=corpus_max_files,
        max_terms=corpus_max_terms,
    )
    contract = SANDBOX / "prism_pinset_swap_contract_v1.json"
    registry = ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"
    pinset = select_pinset(
        registry_path=registry,
        contract_path=contract,
        task_profile="py_coding",
        selection_mode="fixed_preferred",
    )
    pinset_block = format_pinset_block(pinset)

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

        rows.append(
            {
                "id": item.get("id"),
                "lane": item.get("lane"),
                "no_guard_baseline": _slim(baseline),
                "no_guard_meta_only": _slim(meta_only),
                "no_guard_meta_corpus": _slim(meta_corpus),
                "meta_only_preserves_baseline": (
                    baseline.get("reconstruction_fidelity_jaccard")
                    == meta_only.get("reconstruction_fidelity_jaccard")
                ),
                "meta_corpus_preserves_baseline": (
                    baseline.get("reconstruction_fidelity_jaccard")
                    == meta_corpus.get("reconstruction_fidelity_jaccard")
                ),
                "corpus_delta_jaccard": (
                    float(meta_corpus.get("reconstruction_fidelity_jaccard") or 0)
                    - float(baseline.get("reconstruction_fidelity_jaccard") or 0)
                    if meta_corpus.get("reconstruction_fidelity_jaccard") is not None
                    and baseline.get("reconstruction_fidelity_jaccard") is not None
                    else None
                ),
            }
        )

    base_rows = [r["no_guard_baseline"] for r in rows]
    meta_rows = [r["no_guard_meta_only"] for r in rows]
    corp_rows = [r["no_guard_meta_corpus"] for r in rows]

    return {
        "schema": "prism_no_guard_meta_corpus_bench_v1",
        "lane": "D_no_guard_meta_corpus_triple",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "no_guard_profile": str(no_guard_profile.relative_to(ROOT)).replace("\\", "/"),
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "corpus_expansion": {
            **corpus_meta,
            "must_keep_extra_count": len(must_keep_extra),
            "simulated_bloat": True,
            "production_lexicon_mutated": False,
        },
        "aggregate": {
            "baseline_avg_jaccard": _avg(base_rows, "reconstruction_fidelity_jaccard"),
            "meta_only_avg_jaccard": _avg(meta_rows, "reconstruction_fidelity_jaccard"),
            "meta_corpus_avg_jaccard": _avg(corp_rows, "reconstruction_fidelity_jaccard"),
            "baseline_min_jaccard": min(
                (r["reconstruction_fidelity_jaccard"] for r in base_rows if r.get("reconstruction_fidelity_jaccard") is not None),
                default=None,
            ),
            "meta_only_preserves_count": sum(1 for r in rows if r.get("meta_only_preserves_baseline")),
            "meta_corpus_preserves_count": sum(1 for r in rows if r.get("meta_corpus_preserves_baseline")),
            "corpus_worsened_jaccard_count": sum(
                1 for r in rows if (r.get("corpus_delta_jaccard") or 0) < -0.01
            ),
        },
        "cases": rows,
        "interpretation_ko": {
            "triple_axis": "baseline vs meta-only vs meta+corpus must_keep bloat",
            "note": "corpus bloat affects compress path only when passed as must_keep_extra",
        },
        "boundary_ack": "Simulated must_keep; lexicon SSOT untouched.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="No-Guard meta+corpus triple bench (D).")
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
            f"b_jac={agg.get('baseline_avg_jaccard')} "
            f"meta={agg.get('meta_only_avg_jaccard')} "
            f"corp={agg.get('meta_corpus_avg_jaccard')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
