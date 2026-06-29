#!/usr/bin/env python3
"""P3-Root-Generator bench gate v1 — extension/replacement profile decision (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT = ROOT / "docs/final/artifacts/P3_ROOT_GENERATOR_BENCH_CONTRACT_V1.json"
DEFAULT_BENCH = ROOT / "reports/p3_root_generator_bench_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/p3_root_generator_bench_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _evaluate(profile: str, gates: dict[str, Any], bench: dict[str, Any]) -> tuple[str, list[str]]:
    cmp_ = bench.get("comparison") or {}
    reasons: list[str] = []
    if cmp_.get("same_lexicon"):
        reasons.append("candidate_same_as_baseline")
        return "HOLD", reasons

    retention = cmp_.get("atom_retention") or {}
    oov_delta = float(cmp_.get("oov_hit_ratio_delta") or 0.0)
    nsm_delta = float(cmp_.get("nsm_prime_hit_rate_delta") or 0.0)
    router_lex_delta = cmp_.get("router_probe_lexicon_hit_rate_delta")
    comp_delta = cmp_.get("compression_delta") or {}
    jaccard_delta = float(comp_delta.get("jaccard_delta_candidate_minus_baseline") or 0.0)
    saving_delta = float(comp_delta.get("saving_delta_candidate_minus_baseline") or 0.0)

    if profile == "extension":
        min_ret = float(gates.get("baseline_atom_id_retention_rate_min", 1.0))
        min_oov = float(gates.get("oov_fixture_hit_rate_delta_min", 0.0))
        max_j_drop = float(gates.get("compression_jaccard_drop_max_pp", 0.02))
        max_s_drop = float(gates.get("compression_saving_drop_max_pp", 0.03))
        min_router_lex = float(gates.get("router_probe_lexicon_hit_rate_delta_min", 0.0))

        if float(retention.get("retention_rate") or 0.0) < min_ret:
            reasons.append("baseline_atom_retention_below_min")
        if oov_delta < min_oov:
            reasons.append("oov_hit_delta_below_min")
        if jaccard_delta < -max_j_drop:
            reasons.append("compression_jaccard_drop_exceeds_max")
        if saving_delta < -max_s_drop:
            reasons.append("compression_saving_drop_exceeds_max")
        if router_lex_delta is not None and float(router_lex_delta) < min_router_lex:
            reasons.append("router_probe_lexicon_hit_delta_below_min")

        shallow = bench.get("shallow_router_slice") or {}
        min_shallow = gates.get("shallow_router_hit_rate_min")
        if min_shallow is not None and not shallow.get("skipped"):
            rate = shallow.get("router_hit_rate")
            if rate is not None and float(rate) < float(min_shallow):
                reasons.append("shallow_router_hit_rate_below_min")

        if not reasons:
            return "ADVANCE_EXTENSION_CANDIDATE", ["all_extension_gates_pass"]
        return "HOLD", reasons

    min_oov = float(gates.get("oov_fixture_hit_rate_delta_min", 0.1))
    min_j = float(gates.get("compression_jaccard_delta_min_pp", 0.0))
    min_s = float(gates.get("compression_saving_delta_min_pp", 0.0))
    min_nsm = float(gates.get("nsm_crosswalk_sample_hit_rate_min", 0.5))

    c_nsm = float(((bench.get("candidate") or {}).get("nsm_crosswalk") or {}).get("prime_hit_rate") or 0.0)

    if oov_delta < min_oov:
        reasons.append("oov_hit_delta_below_min")
    if jaccard_delta < min_j:
        reasons.append("compression_jaccard_not_improved")
    if saving_delta < min_s:
        reasons.append("compression_saving_not_improved")
    if c_nsm < min_nsm:
        reasons.append("nsm_crosswalk_hit_rate_below_min")
    min_router_lex = float(gates.get("router_probe_lexicon_hit_rate_delta_min", 0.0))
    if router_lex_delta is not None and float(router_lex_delta) < min_router_lex:
        reasons.append("router_probe_lexicon_hit_delta_below_min")
    min_rows = int(gates.get("candidate_row_count_min") or 0)
    cand_rows = int(((bench.get("candidate") or {}).get("meta") or {}).get("row_count") or 0)
    if min_rows and cand_rows < min_rows:
        reasons.append("candidate_row_count_below_min")

    if not reasons:
        return "ADVANCE_REPLACEMENT_RESEARCH", ["all_replacement_gates_pass"]
    return "HOLD", reasons


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, default=CONTRACT)
    ap.add_argument("--bench", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 unless decision != HOLD")
    args = ap.parse_args()

    if not args.contract.is_file() or not args.bench.is_file():
        print("ABORT: contract or bench report missing")
        return 1

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    bench = json.loads(args.bench.read_text(encoding="utf-8"))
    profile = str(bench.get("profile") or "extension")
    profiles = contract.get("profiles") or {}
    prof = profiles.get(profile) or {}
    gates = prof.get("primary_gates") or {}
    decision, reasons = _evaluate(profile, gates, bench)

    out = {
        "schema": "p3_root_generator_bench_gate_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "profile": profile,
        "decision": decision,
        "reasons": reasons,
        "inputs": {
            "contract": _rel(args.contract),
            "bench_report": _rel(args.bench),
        },
        "primary_gates": gates,
        "comparison_snapshot": bench.get("comparison"),
        "note_ko": "ADVANCE_* = B-track research only; production pointer swap still forbidden without commander signoff.",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(args.out), "decision": decision, "reasons": reasons}, ensure_ascii=False))

    if args.strict and decision == "HOLD":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
