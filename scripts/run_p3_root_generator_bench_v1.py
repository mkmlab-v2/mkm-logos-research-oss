#!/usr/bin/env python3
"""P3-Root-Generator bench v1 — baseline 41k vs candidate lexicon A/B (B-track, offline)."""

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

from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    _load_lexicon_index,
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.p3_root_generator_lib_v1 import router_probe_metrics, shallow_router_slice  # noqa: E402
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

ROUTER_PROBE = ROOT / "tests/fixtures/p3_root_router_probe_v1.json"

CONTRACT = ROOT / "docs/final/artifacts/P3_ROOT_GENERATOR_BENCH_CONTRACT_V1.json"
DEFAULT_OUT = ROOT / "reports/p3_root_generator_bench_v1_latest.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _lexicon_meta(path: Path) -> dict[str, Any]:
    doc = _load_json(path)
    entries = doc.get("entries") or []
    atom_ids = {
        str(e.get("atom_id"))
        for e in entries
        if isinstance(e, dict) and e.get("atom_id")
    }
    forms, _ = _load_lexicon_index(str(path.resolve()))
    return {
        "path": _rel(path),
        "row_count": int(doc.get("row_count") or len(entries)),
        "unique_normalized_forms": len(forms),
        "unique_atom_ids": len(atom_ids),
        "schema": doc.get("schema"),
        "overlay_meta": doc.get("overlay_meta") or doc.get("export_candidate_meta"),
    }


def _oov_fixture_metrics(path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    per_case = []
    total = 0
    hits = 0
    for case in fixture.get("cases") or []:
        tokens = [str(t).strip().lower() for t in (case.get("tokens") or []) if str(t).strip()]
        case_hits: list[str] = []
        case_hit_n = 0
        for tok in tokens:
            total += 1
            h, _ = lexicon_hits_for_text(tok, path)
            if h:
                hits += 1
                case_hit_n += 1
                case_hits.extend(sorted(h)[:3])
        per_case.append(
            {
                "id": case.get("id"),
                "domain": case.get("domain"),
                "token_count": len(tokens),
                "hit_count": case_hit_n,
                "hit_ratio": round(case_hit_n / len(tokens), 4) if tokens else 0.0,
                "hits_sample": sorted(set(case_hits))[:6],
            }
        )
    return {
        "aggregate_hit_ratio": round(hits / total, 4) if total else 0.0,
        "total_tokens": total,
        "total_hits": hits,
        "per_case": per_case,
    }


def _nsm_crosswalk_metrics(path: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    rows = []
    passed = 0
    total = 0
    for sample in fixture.get("samples") or []:
        probes = [str(t).strip().lower() for t in (sample.get("probe_tokens") or []) if str(t).strip()]
        prime = str(sample.get("prime_en") or "")
        hit_any = False
        hit_tokens: list[str] = []
        for tok in probes:
            total += 1
            h, _ = lexicon_hits_for_text(tok, path)
            if h:
                hit_any = True
                hit_tokens.extend(sorted(h)[:2])
        if hit_any:
            passed += 1
        rows.append(
            {
                "prime_en": prime,
                "probe_count": len(probes),
                "any_probe_hit": hit_any,
                "hits_sample": sorted(set(hit_tokens))[:4],
            }
        )
    return {
        "sample_count": len(rows),
        "prime_hit_rate": round(passed / len(rows), 4) if rows else 0.0,
        "probe_token_hit_rate": round(
            sum(1 for r in rows if r["any_probe_hit"]) / len(rows), 4
        )
        if rows
        else 0.0,
        "rows": rows,
    }


def _atom_retention(baseline: Path, candidate: Path) -> dict[str, Any]:
    b_doc = _load_json(baseline)
    c_doc = _load_json(candidate)
    b_atoms = {
        str(e.get("atom_id"))
        for e in (b_doc.get("entries") or [])
        if isinstance(e, dict) and e.get("atom_id")
    }
    c_atoms = {
        str(e.get("atom_id"))
        for e in (c_doc.get("entries") or [])
        if isinstance(e, dict) and e.get("atom_id")
    }
    missing = sorted(b_atoms - c_atoms)
    added = sorted(c_atoms - b_atoms)
    rate = round(len(b_atoms & c_atoms) / len(b_atoms), 6) if b_atoms else 0.0
    return {
        "baseline_atom_count": len(b_atoms),
        "candidate_atom_count": len(c_atoms),
        "retained_atom_count": len(b_atoms & c_atoms),
        "retention_rate": rate,
        "missing_from_candidate_count": len(missing),
        "added_in_candidate_count": len(added),
        "missing_sample": missing[:8],
        "added_sample": added[:8],
    }


def _compression_sample(
    lexicon_path: Path,
    *,
    max_cases: int,
) -> dict[str, Any] | None:
    if max_cases <= 0 or not INPUT_V2.is_file():
        return None
    src = _load_json(INPUT_V2)
    cases = (src.get("compression_cases") or [])[:max_cases]
    if not cases:
        return None
    subset = dict(src)
    subset["compression_cases"] = cases
    baseline = _load_json(BASELINE_V2) if BASELINE_V2.is_file() else {}
    decision = _load_json(DECISION) if DECISION.is_file() else {}
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    report = evaluate_report(
        subset,
        source_input=_rel(INPUT_V2),
        mode="experimental",
        strategy=str(selected.get("strategy", "A")),
        intensity=str(selected.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=float(selected.get("general_max_saving_rate", 0.35)),
        sensitive_max_saving_rate=float(selected.get("sensitive_max_saving_rate", 0.3)),
        hangul_max_saving_rate=float(selected.get("hangul_max_saving_rate", 0.6)),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_path=lexicon_path,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=False,
        include_cee_core=True,
    )
    cm = report.get("compression_metrics") or {}
    return {
        "sample_case_count": len(cases),
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "avg_sensitive_integrity": cm.get("avg_sensitive_integrity"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", type=Path, default=CONTRACT)
    ap.add_argument("--profile", choices=("extension", "replacement"), default=None)
    ap.add_argument("--baseline-lexicon", type=Path, default=None)
    ap.add_argument("--candidate-lexicon", type=Path, default=None)
    ap.add_argument("--compression-sample", type=int, default=None)
    ap.add_argument("--no-router-probe", action="store_true")
    ap.add_argument("--include-shallow-router-slice", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.contract.is_file():
        print(f"ABORT: contract missing: {args.contract}")
        return 1

    contract = _load_json(args.contract)
    profile = args.profile or str(
        ((contract.get("philosophy") or {}).get("default_mode")) or "extension"
    )
    fixtures = contract.get("fixtures") or {}
    oov_path = ROOT / str(fixtures.get("oov_cases", ""))
    nsm_path = ROOT / str(fixtures.get("nsm_crosswalk_sample", ""))
    max_cases = args.compression_sample
    if max_cases is None:
        max_cases = int(fixtures.get("compression_sample_max_cases") or 8)

    baseline = args.baseline_lexicon
    if baseline is None:
        anchor = str(
            ((contract.get("philosophy") or {}).get("single_anchor_ssot")) or ""
        )
        baseline = ROOT / anchor if anchor else None
    if baseline is None or not baseline.is_file():
        baseline = resolve_latest_codebook_path()
    if baseline is None or not baseline.is_file():
        print("ABORT: baseline lexicon not found")
        return 1

    candidate = args.candidate_lexicon or baseline
    if candidate is not None:
        candidate = candidate.resolve()
    if baseline is not None:
        baseline = baseline.resolve()

    oov_fixture = _load_json(oov_path) if oov_path.is_file() else {"cases": []}
    nsm_fixture = _load_json(nsm_path) if nsm_path.is_file() else {"samples": []}
    router_fixture = _load_json(ROUTER_PROBE) if ROUTER_PROBE.is_file() else {"probes": []}

    include_router = not args.no_router_probe
    b_router = router_probe_metrics(baseline, router_fixture) if include_router else None
    c_router = router_probe_metrics(candidate, router_fixture) if include_router else None
    shallow_slice = shallow_router_slice(skip_ollama=True) if args.include_shallow_router_slice else None

    b_oov = _oov_fixture_metrics(baseline, oov_fixture)
    c_oov = _oov_fixture_metrics(candidate, oov_fixture)
    b_nsm = _nsm_crosswalk_metrics(baseline, nsm_fixture)
    c_nsm = _nsm_crosswalk_metrics(candidate, nsm_fixture)
    retention = _atom_retention(baseline, candidate)
    b_comp = _compression_sample(baseline, max_cases=max_cases)
    c_comp = _compression_sample(candidate, max_cases=max_cases)

    comp_delta: dict[str, Any] = {}
    if b_comp and c_comp:
        comp_delta = {
            "saving_delta_candidate_minus_baseline": (c_comp.get("global_token_saving_rate") or 0)
            - (b_comp.get("global_token_saving_rate") or 0),
            "jaccard_delta_candidate_minus_baseline": (
                c_comp.get("avg_reconstruction_fidelity_jaccard") or 0
            )
            - (b_comp.get("avg_reconstruction_fidelity_jaccard") or 0),
        }

    out = {
        "schema": "p3_root_generator_bench_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "profile": profile,
        "note_ko": "41k frozen anchor vs candidate. NOT Track A promotion. Extension=overlay; replacement=full swap research.",
        "inputs": {
            "contract": _rel(args.contract),
            "oov_fixture": _rel(oov_path) if oov_path.is_file() else None,
            "nsm_fixture": _rel(nsm_path) if nsm_path.is_file() else None,
            "compression_input": _rel(INPUT_V2) if INPUT_V2.is_file() else None,
            "compression_sample_max_cases": max_cases,
            "router_probe": _rel(ROUTER_PROBE) if include_router and ROUTER_PROBE.is_file() else None,
            "shallow_router_slice": bool(args.include_shallow_router_slice),
        },
        "baseline": {
            "meta": _lexicon_meta(baseline),
            "oov": b_oov,
            "nsm_crosswalk": b_nsm,
            "compression_sample": b_comp,
            "router_probe": b_router,
        },
        "candidate": {
            "meta": _lexicon_meta(candidate),
            "oov": c_oov,
            "nsm_crosswalk": c_nsm,
            "compression_sample": c_comp,
            "router_probe": c_router,
        },
        "comparison": {
            "same_lexicon": baseline.resolve() == candidate.resolve(),
            "atom_retention": retention,
            "oov_hit_ratio_delta": round(
                c_oov["aggregate_hit_ratio"] - b_oov["aggregate_hit_ratio"], 4
            ),
            "nsm_prime_hit_rate_delta": round(
                c_nsm["prime_hit_rate"] - b_nsm["prime_hit_rate"], 4
            ),
            "compression_delta": comp_delta,
            "router_probe_lexicon_hit_rate_delta": round(
                (c_router or {}).get("lexicon_token_hit_rate", 0)
                - (b_router or {}).get("lexicon_token_hit_rate", 0),
                4,
            )
            if b_router and c_router
            else None,
            "router_probe_domain_hit_rate_baseline": (b_router or {}).get("domain_router_hit_rate"),
            "router_probe_domain_hit_rate_candidate": (c_router or {}).get("domain_router_hit_rate"),
        },
        "shallow_router_slice": shallow_slice,
        "gate_preview": {
            "profile": profile,
            "expected_default_decision": "HOLD",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": _rel(args.out),
                "profile": profile,
                "baseline_rows": out["baseline"]["meta"]["row_count"],
                "candidate_rows": out["candidate"]["meta"]["row_count"],
                "oov_delta": out["comparison"]["oov_hit_ratio_delta"],
                "router_lexicon_delta": out["comparison"].get("router_probe_lexicon_hit_rate_delta"),
                "same_lexicon": out["comparison"]["same_lexicon"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
