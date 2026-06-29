#!/usr/bin/env python3
"""[HYPO] Path A — masked customer JSONL cohort (20–50 rows) spine + 1:1 ROI proxy.

Synthetic masked local rehearsal — NOT real customer data.
research_only · send_gate HOLD · never merge with latent 47% headline.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/ng40_path_a_customer_masked_cohort_chain_v1_latest.json"
TACTICAL_JSONL = ROOT / "data/compression/tactical_b_free_audit_pilot_v1.jsonl"
BENCH_OUT = ROOT / "data/compression/tactical_b_free_audit_spine_bench_v1.json"
SPINE_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_path_a_customer_masked_spine_eval_v1_latest.json"
)
PATH_A_SPINE_BASELINE = 0.222911
TENANT_ID = "path-a-masked-cohort-v1"
SCHEMA = "ng40_path_a_customer_masked_cohort_chain_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=25)
    ap.add_argument("--skip-corpus-build", action="store_true")
    ap.add_argument("--skip-spine-eval", action="store_true")
    ap.add_argument("--skip-roi-chain", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_corpus_build:
        steps.append(
            _run(
                "tactical_b_corpus",
                [
                    PY,
                    "scripts/build_compression_tactical_b_free_audit_corpus_v1.py",
                    "--rows",
                    str(args.rows),
                ],
            )
        )
        steps.append(
            _run(
                "spine_bench_input",
                [
                    PY,
                    "scripts/build_compression_customer_jsonl_spine_bench_v1.py",
                    "--jsonl",
                    str(TACTICAL_JSONL.relative_to(ROOT)).replace("\\", "/"),
                    "--out-json",
                    str(BENCH_OUT.relative_to(ROOT)).replace("\\", "/"),
                    "--max-cases",
                    str(args.rows),
                ],
            )
        )

    if not args.skip_spine_eval:
        steps.append(
            _run(
                "path_a_spine_eval",
                [
                    PY,
                    "scripts/run_nextgen_spine_binary_billable_eval_v1.py",
                    "--bench-input",
                    str(BENCH_OUT.relative_to(ROOT)).replace("\\", "/"),
                    "--out-json",
                    str(SPINE_EVAL.relative_to(ROOT)).replace("\\", "/"),
                    "--arm-id",
                    "ng40_path_a_customer_masked_spine_v1",
                    "--bench-label",
                    "customer_masked_tactical_b",
                ],
            )
        )

    if not args.skip_roi_chain:
        steps.append(
            _run(
                "pilot_roi_proxy",
                [
                    PY,
                    "scripts/run_compression_pilot_roi_chain_v1.py",
                    "--tenant-id",
                    TENANT_ID,
                    "--input-jsonl",
                    str(TACTICAL_JSONL.relative_to(ROOT)).replace("\\", "/"),
                    "--max-cases",
                    str(args.rows),
                    "--compression-profile",
                    "fidelity",
                    "--relax-pass-gate",
                ],
            )
        )

    spine = _load(SPINE_EVAL) or {}
    agg = spine.get("aggregate") or {}
    spine_saving = float(agg.get("global_token_saving_rate_spine_binary_billable") or agg.get("global_token_saving_rate") or 0)
    byte_exact = float(agg.get("byte_exact_subset_parity") or 0)
    roi_chain = _load(ROOT / "reports/compression_pilot_roi_chain_v1_latest.json") or {}
    poc_path = ROOT / f"reports/customer_compression_stateless_poc_{TENANT_ID}_v1_latest.json"
    poc = _load(poc_path) or {}
    poc_agg = poc.get("aggregate") or poc

    spine_matches_path_a = byte_exact >= 1.0
    spine_delta_vs_b2b_pp = round((spine_saving - PATH_A_SPINE_BASELINE) * 100, 2)
    chain_ok = all(s["exit_code"] == 0 for s in steps)

    report = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "customer_provided": False,
        "synthetic_masked_rehearsal": True,
        "chain_ok": chain_ok,
        "steps": steps,
        "cohort": {
            "source_jsonl": str(TACTICAL_JSONL.relative_to(ROOT)).replace("\\", "/"),
            "row_count": args.rows,
            "tenant_id": TENANT_ID,
        },
        "path_a_spine_eval": {
            "pointer": str(SPINE_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "global_token_saving_rate_spine_binary": spine_saving,
            "byte_exact_subset_parity": byte_exact,
            "path_a_b2b_baseline": PATH_A_SPINE_BASELINE,
            "spine_byte_exact_ok": spine_matches_path_a,
            "cohort_note": "support-chat masked cohort ≠ B2B longform — saving % not required to match 22.29%",
            "spine_saving_delta_vs_b2b_baseline_pp": spine_delta_vs_b2b_pp,
        },
        "pilot_roi_proxy": {
            "chain_pointer": "reports/compression_pilot_roi_chain_v1_latest.json",
            "poc_pointer": str(poc_path.relative_to(ROOT)).replace("\\", "/") if poc else None,
            "mean_token_saving_rate_proxy": poc_agg.get("mean_token_saving_rate_proxy")
            or poc_agg.get("mean_token_saving_rate"),
            "mean_jaccard_proxy": poc_agg.get("mean_jaccard_proxy")
            or poc_agg.get("mean_reconstruction_fidelity_jaccard"),
            "note": "1:1 list-price proxy — not billing commitment; ≠ Track A 47%",
        },
        "fail_comp_004": {
            "latent_47_headline_forbidden": True,
            "repair_v2_not_track_a_promotion": True,
            "cohort_labeled_synthetic": True,
        },
        "verdict_ko": [
        f"Path A spine masked cohort: {spine_saving*100:.2f}% byte_exact={byte_exact}",
        f"B2B longform baseline (reference only): {PATH_A_SPINE_BASELINE*100:.2f}% — cohort delta {spine_delta_vs_b2b_pp}pp",
            "ROI proxy fidelity profile — counsel before external send",
        ],
        "reproducible_command": "py scripts/run_ng40_path_a_customer_masked_cohort_chain_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "chain_ok": chain_ok,
                "spine_saving": spine_saving,
                "spine_invariant": spine_matches_path_a,
                "out": str(OUT),
            },
            ensure_ascii=False,
        )
    )
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
