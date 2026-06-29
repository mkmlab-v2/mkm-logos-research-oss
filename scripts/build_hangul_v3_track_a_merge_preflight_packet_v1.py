#!/usr/bin/env python3
"""Track A v3 merge preflight packet — Golden-40 compare + promotion gates (no pointer swap)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_master_codebook_golden40_lexicon_ab_v1 import (  # noqa: E402
    _load_signoff_relaxed,
    _metrics,
    _run_eval,
)
from scripts.hangul_v3_track_a_merge_lib_v1 import count_ko, row_count, subset_audit  # noqa: E402
from scripts.run_ultra_compression_default import INPUT_V2  # noqa: E402

CONTRACT = ROOT / "docs/final/artifacts/HANGUL_V3_TRACK_A_MERGE_PREFLIGHT_CONTRACT_V1.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"
PROD = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
V3 = PILOT / "master_codebook_lexicon_v1_41676_hangul_curated_export_candidate_v3_golden40_evidence.json"
CANDIDATE = PILOT / "master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v3_track_a_merge_preflight.json"
POINTER = PILOT / "master_codebook_bench_lexicon_pointer_v1_latest.json"
BUILD_REPORT = ROOT / "reports/hangul_v3_track_a_merge_candidate_build_v1_latest.json"
OUT = ROOT / "reports/hangul_v3_track_a_merge_preflight_packet_v1_latest.json"

GATE2_MIN_DELTA_SAVING = -0.02
GATE2_MIN_DELTA_JACCARD = -0.02


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, default=CANDIDATE)
    ap.add_argument("--production", type=Path, default=PROD)
    ap.add_argument("--v3-candidate", type=Path, default=V3)
    ap.add_argument("--build-report", type=Path, default=BUILD_REPORT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    prod_path = args.production.resolve()
    cand_path = args.candidate.resolve()
    v3_path = args.v3_candidate.resolve()
    missing = [p for p in (prod_path, cand_path, v3_path, INPUT_V2) if not p.is_file()]
    if missing:
        print("ABORT: missing", [str(m) for m in missing])
        return 1

    contract = json.loads(CONTRACT.read_text(encoding="utf-8")) if CONTRACT.is_file() else {}
    gates_cfg = contract.get("gates") or {}
    prod_doc = json.loads(prod_path.read_text(encoding="utf-8"))
    v3_doc = json.loads(v3_path.read_text(encoding="utf-8"))
    cand_doc = json.loads(cand_path.read_text(encoding="utf-8"))
    pointer = json.loads(POINTER.read_text(encoding="utf-8")) if POINTER.is_file() else {}

    src = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    relaxed, allow, exclude = _load_signoff_relaxed()
    m_prod = _metrics(
        _run_eval(
            src,
            lexicon_path=prod_path,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    )
    m_cand = _metrics(
        _run_eval(
            src,
            lexicon_path=cand_path,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    )
    m_v3_naive = _metrics(
        _run_eval(
            src,
            lexicon_path=v3_path,
            domain_relaxed=relaxed,
            relaxed_case_allowlist=allow,
            relaxed_case_exclude=exclude,
        )
    )

    delta_saving = (m_cand.get("global_token_saving_rate") or 0) - (m_prod.get("global_token_saving_rate") or 0)
    delta_j = (m_cand.get("avg_reconstruction_fidelity_jaccard") or 0) - (
        m_prod.get("avg_reconstruction_fidelity_jaccard") or 0
    )
    v3_vs_prod_saving = (m_v3_naive.get("global_token_saving_rate") or 0) - (
        m_prod.get("global_token_saving_rate") or 0
    )

    subset = subset_audit(prod_doc, v3_doc)
    prod_ko = count_ko(prod_doc)
    cand_ko = count_ko(cand_doc)
    prod_rows = row_count(prod_doc)
    cand_rows = row_count(cand_doc)

    ko_delta_min = int(gates_cfg.get("ko_cardinality_min_vs_production", 0))
    saving_min = float(gates_cfg.get("golden40_delta_saving_min", GATE2_MIN_DELTA_SAVING))
    jaccard_min = float(gates_cfg.get("golden40_delta_jaccard_min", GATE2_MIN_DELTA_JACCARD))

    checks: dict[str, bool] = {
        "v3_subset_of_production": bool(subset.get("v3_is_subset_of_production")),
        "naive_v3_swap_blocked": bool(subset.get("naive_v3_swap_regresses_ko")),
        "ko_cardinality_vs_production": cand_ko >= prod_ko + ko_delta_min,
        "row_count_no_shrink": cand_rows >= prod_rows,
        "golden40_delta_saving_pass": delta_saving >= saving_min,
        "golden40_delta_jaccard_pass": delta_j >= jaccard_min,
        "sensitive_violation_unchanged": int(m_cand.get("sensitive_violation_count") or 0)
        == int(m_prod.get("sensitive_violation_count") or 0),
    }
    preflight_ready = all(checks.values())
    scope_locks = {
        "production_pointer_swap_blocked": True,
        "multilens_active_write_blocked": True,
    }

    prod_ssot = pointer.get("production_ssot") or {}
    doc: dict[str, Any] = {
        "schema": "hangul_v3_track_a_merge_preflight_packet_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "send_gate": "HOLD",
        "merge_profile": (cand_doc.get("export_candidate_meta") or {}).get("merge_profile"),
        "contract": _rel(CONTRACT) if CONTRACT.is_file() else None,
        "philosophy_summary": {
            "production_ko": prod_ko,
            "v3_ko": count_ko(v3_doc),
            "merge_candidate_ko": cand_ko,
            "v3_is_strict_subset": subset.get("v3_is_subset_of_production"),
            "prod_only_ko_count": subset.get("prod_only_count"),
            "recommended_path": "41708 base + v2 50-lemma overlay; not standalone v3 41676 swap",
        },
        "paths": {
            "production_lexicon": _rel(prod_path),
            "v3_export_candidate": _rel(v3_path),
            "merge_candidate": _rel(cand_path),
            "build_report": _rel(args.build_report) if args.build_report.is_file() else None,
            "production_pointer": _rel(POINTER) if POINTER.is_file() else None,
        },
        "subset_audit": subset,
        "golden40_compare": {
            "baseline_lexicon": _rel(prod_path),
            "baseline": m_prod,
            "merge_candidate": m_cand,
            "naive_v3_standalone": m_v3_naive,
            "delta_merge_vs_production": {
                "global_token_saving_rate": delta_saving,
                "avg_reconstruction_fidelity_jaccard": delta_j,
            },
            "delta_naive_v3_vs_production": {
                "global_token_saving_rate": v3_vs_prod_saving,
            },
        },
        "lane_kpi_pointer_intent": {
            "pointer_golden40_saving": (prod_ssot.get("golden40_kpi") or {}).get("global_token_saving_rate"),
            "pointer_golden40_jaccard": (prod_ssot.get("golden40_kpi") or {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "note": "FAIL-COMP-004: cite lane; do not collapse pointer vs ACTIVE disk vs merge candidate",
        },
        "preflight_gates": checks,
        "scope_locks": scope_locks,
        "preflight_ready": preflight_ready,
        "promotion_scope": {
            "production_ssot_swap": False,
            "multilens_active_report_write": False,
            "ms_paste_headline_auto_update": False,
            "send_gate_unlock": False,
            "next_step_after_commander": "separate Track A signoff + apply chain (not this preflight)",
        },
        "forbidden": contract.get("forbidden") or [],
        "reproduce": "py scripts/run_hangul_v3_track_a_merge_preflight_chain_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(out_path), "preflight_ready": preflight_ready}, ensure_ascii=False))
    return 0 if preflight_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
