#!/usr/bin/env python3
"""[HYPO] Step 1/2: NG-40 codec/bench split — latent vs spine vs hybrid lanes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "experiments/nextgen_clean_slate_cpu_v1/NG40_CODEC_BENCH_SPLIT_SPEC_V1.json"
OUT_MANIFEST = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json"
)
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"script": script, "args": extra or [], "exit_code": int(cp.returncode), "parsed": parsed}


def _load_json(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-path-b-sweep", action="store_true", help="Skip 320-combo sweep (slow)")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    frozen_cm: dict[str, Any] = {}
    if ACTIVE.is_file():
        cm = json.loads(ACTIVE.read_text(encoding="utf-8-sig")).get("compression_metrics") or {}
        frozen_cm = {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": cm.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        }

    steps.append(_run("scripts/run_nextgen_byte_exact_subset_audit_v1.py"))
    steps.append(_run("scripts/run_nextgen_verbatim_spine_bench_v1.py"))
    steps.append(
        _run(
            "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
            ["--keep-ratio", "0.88"],
        )
    )
    steps.append(_run("scripts/run_nextgen_hybrid_spine_trilane_stack_v1.py"))
    steps.append(_run("scripts/run_nextgen_guarded_b2b_decode_contract_v1.py"))
    steps.append(_run("scripts/run_ng40_path_b_prior_41k_eval_v1.py"))
    if not args.skip_path_b_sweep:
        steps.append(_run("scripts/run_ng40_path_b_dual_axis_push_v1.py", ["--skip-promotion-packet"]))
    steps.append(_run("scripts/run_nextgen_commercialization_pareto_sweep_v1.py"))

    prior = _load_json(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_path_b_prior_41k_v1_latest.json"
    )
    hybrid = _load_json(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
    )
    guarded = _load_json(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
    )
    spine = _load_json(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_verbatim_spine_bench_v1_latest.json"
    )
    path_b = _load_json("reports/ng40_path_b_dual_axis_push_v1_latest.json")

    manifest = {
        "schema": "ng40_codec_bench_split_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "spec_pointer": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "frozen_active": frozen_cm,
        "lanes": {
            "latent_golden40_dual_axis": {
                "prior_41k": {
                    "beat_frozen": (prior or {}).get("beat_check", {}).get("beat_frozen"),
                    "saving": (prior or {}).get("aggregate", {}).get("global_token_saving_rate"),
                    "jaccard": (prior or {}).get("aggregate", {}).get(
                        "avg_reconstruction_fidelity_jaccard"
                    ),
                },
                "path_b_sweep_any_beat": (path_b or {}).get("any_beat_frozen_vs_active"),
            },
            "spine_byte_exact_b2b": {
                "verbatim_spine_byte_exact": (spine or {}).get("aggregate", {}).get(
                    "byte_exact_subset_parity"
                ),
                "guarded_contract_met": bool(
                    ((guarded or {}).get("aggregate") or {}).get("contract_met")
                    or (guarded or {}).get("contract_met")
                ),
                "guarded_byte_exact": (
                    ((guarded or {}).get("aggregate") or {}).get("byte_exact_subset_parity")
                    or (guarded or {}).get("byte_exact_subset_parity")
                ),
            },
            "hybrid_sidecar_preview": {
                "keep_ratio": 0.88,
                "byte_exact_parity": (hybrid or {}).get("aggregate", {}).get(
                    "byte_exact_subset_parity"
                ),
                "sidecar_jaccard": (hybrid or {}).get("aggregate", {}).get(
                    "avg_reconstruction_fidelity_jaccard"
                ),
            },
        },
        "conclusion_ko": (
            "latent dual-axis: ACTIVE 미달 가능성 높음(cap만). "
            "상품 완성은 hybrid+guarded spine 레인."
        ),
        "steps": steps,
        "next_chain": "scripts/run_ng40_path_a_product_signoff_chain_v1.py",
    }
    # fix typo true -> True in python - I used true in dict by mistake
    manifest["research_only"] = True

    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(OUT_MANIFEST), "lanes": list(manifest["lanes"].keys())}, ensure_ascii=False))
    hard = any(s["exit_code"] != 0 for s in steps[:6])
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
