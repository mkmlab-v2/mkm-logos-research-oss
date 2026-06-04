#!/usr/bin/env python3
"""[HYPO] Golden-40 eval on one shard (case subset) for distributed PoC."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_nextgen_latent_indexer_eval_ng40_v1 import (
    INPUT_V2,
    _beat,
    _frozen_active,
    evaluate_ng40_lane,
)

DEFAULT_OUT_DIR = ROOT / "experiments/nextgen_clean_slate_cpu_v1/results"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shard_cases(cases: list[dict], shard_index: int, shard_count: int) -> list[dict]:
    if shard_count < 1:
        return cases
    return [c for i, c in enumerate(cases) if i % shard_count == shard_index]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bench-input", type=Path, default=INPUT_V2)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=2)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--general-cap", type=float, default=0.35)
    ap.add_argument("--sensitive-cap", type=float, default=0.30)
    ap.add_argument("--hangul-cap", type=float, default=0.60)
    ap.add_argument("--match-active-caps", action="store_true")
    ap.add_argument("--with-domain-relaxed", action="store_true")
    ap.add_argument("--with-41k-lexicon", action="store_true")
    ap.add_argument("--active-track-parity", action="store_true")
    args = ap.parse_args()

    if args.match_active_caps:
        args.general_cap, args.sensitive_cap, args.hangul_cap = 0.35, 0.30, 0.60
        args.with_domain_relaxed = True
        args.with_41k_lexicon = True
        args.active_track_parity = True

    doc = json.loads(args.bench_input.read_text(encoding="utf-8-sig"))
    comp = doc.get("compression_cases") or []
    fus = doc.get("fusion_answer_cases") or []
    shard_doc = {
        **doc,
        "compression_cases": _shard_cases(comp, args.shard_index, args.shard_count),
        "fusion_answer_cases": _shard_cases(fus, args.shard_index, args.shard_count),
    }
    baseline_j = 0.0
    agg, report = evaluate_ng40_lane(
        shard_doc,
        bench_input=args.bench_input,
        general_cap=args.general_cap,
        sensitive_cap=args.sensitive_cap,
        hangul_cap=args.hangul_cap,
        baseline_j=baseline_j,
        use_domain_relaxed=args.with_domain_relaxed,
        use_master_codebook_lexicon_v1=args.with_41k_lexicon,
        active_track_parity=args.active_track_parity,
    )
    frozen = _frozen_active()
    beat = _beat(agg, frozen)

    out = {
        "schema": "nextgen_ng40_golden40_shard_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "case_count_shard": len(shard_doc["compression_cases"]),
        "aggregate": agg,
        "beat_check": beat,
        "run_config_summary": {
            "general_max_saving_rate": args.general_cap,
            "sensitive_max_saving_rate": args.sensitive_cap,
            "hangul_max_saving_rate": args.hangul_cap,
            "with_domain_relaxed": args.with_domain_relaxed,
            "use_master_codebook_lexicon_v1": args.with_41k_lexicon,
            "active_track_parity": args.active_track_parity,
        },
        "report_pointer": str(args.out_json.with_suffix(".report.json")),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = args.out_json.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "shard": f"{args.shard_index}/{args.shard_count}",
                "cases": out["case_count_shard"],
                "beat_frozen": beat.get("beat_frozen"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
