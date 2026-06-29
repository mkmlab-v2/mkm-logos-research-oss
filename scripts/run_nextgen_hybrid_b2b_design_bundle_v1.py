#!/usr/bin/env python3
"""[HYPO] Hybrid spine + Logos sidecar + guarded B2B contract — design lane bundle."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DESIGN_SPEC = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/HYBRID_B2B_DECODE_DESIGN_V1.json"
)
B2B_BENCH = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_B2B_SPINE_BENCH_INPUT_V1.json"
)
B2B_EVAL_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_b2b_v1_latest.json"
)
HYBRID_STACK_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
)
HYBRID_SWEEP_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_sweep_v1_latest.json"
)
GUARDED_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_b2b_design_bundle_v1_latest.json"
)
DEFAULT_KEEP_RATIOS = (0.75, 0.82, 0.88)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _run(script: str, args: list[str]) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, str(ROOT / script), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout or "").strip().splitlines()
    parsed: dict[str, Any] = {}
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:500]}
    return proc.returncode, {
        "script": script,
        "args": args,
        "exit_code": proc.returncode,
        "parsed": parsed,
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--keep-ratios",
        nargs="*",
        type=float,
        default=list(DEFAULT_KEEP_RATIOS),
    )
    ap.add_argument("--b2b-domain", default="finance_macro_b2b")
    ap.add_argument("--skip-b2b-longform", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc, step = _run(
        "scripts/run_nextgen_guarded_b2b_decode_contract_v1.py",
        ["--out-json", str(GUARDED_OUT)],
    )
    steps.append(step)
    if rc != 0:
        return rc

    sweep_arms: list[dict[str, Any]] = []
    for kr in args.keep_ratios:
        rc, step = _run(
            "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
            ["--keep-ratio", str(kr), "--out-json", str(HYBRID_STACK_OUT)],
        )
        steps.append(step)
        if rc != 0:
            return rc
        doc = _load_json(HYBRID_STACK_OUT) or {}
        agg = doc.get("aggregate") or {}
        sweep_arms.append(
            {
                "keep_ratio": kr,
                "byte_exact_subset_parity": agg.get("byte_exact_subset_parity"),
                "spine_saving": agg.get("global_token_saving_rate_spine_only"),
                "spine_plus_sidecar_saving": agg.get(
                    "global_token_saving_rate_spine_plus_logos_sidecar"
                ),
                "sidecar_jaccard": agg.get("avg_logos_sidecar_jaccard"),
            }
        )

    ratios = [str(k) for k in args.keep_ratios]
    rc, step = _run(
        "scripts/run_nextgen_verbatim_spine_bench_v1.py",
        [
            "--mode",
            "hybrid",
            "--hybrid-sweep",
            *ratios,
            "--out-json",
            str(HYBRID_SWEEP_OUT),
        ],
    )
    steps.append(step)
    if rc != 0:
        return rc

    b2b_eval: dict[str, Any] | None = None
    if not args.skip_b2b_longform:
        rc, step = _run(
            "scripts/build_nextgen_longform_spine_bench_input_v1.py",
            [
                "--domain-tag",
                args.b2b_domain,
                "--min-raw-bytes",
                "256",
                "--max-cases",
                "100",
                "--out-json",
                str(B2B_BENCH),
            ],
        )
        steps.append(step)
        if rc != 0:
            return rc
        rc, step = _run(
            "scripts/run_nextgen_spine_binary_billable_eval_v1.py",
            [
                "--bench-input",
                str(B2B_BENCH),
                "--out-json",
                str(B2B_EVAL_OUT),
                "--arm-id",
                "ng40_spine_binary_billable_b2b_v1",
                "--bench-label",
                "b2b_domain_longform",
            ],
        )
        steps.append(step)
        if rc != 0:
            return rc
        b2b_eval = _load_json(B2B_EVAL_OUT)

    guarded = _load_json(GUARDED_OUT) or {}
    hybrid_sweep = _load_json(HYBRID_SWEEP_OUT) or {}
    g_agg = guarded.get("aggregate") or {}
    contract_met = bool(guarded.get("contract_met") or g_agg.get("contract_met"))
    guarded_byte = guarded.get("byte_exact_subset_parity") or g_agg.get(
        "byte_exact_subset_parity"
    )
    b_agg = (b2b_eval or {}).get("aggregate") or {}
    b2b_byte = (b2b_eval or {}).get("byte_exact_subset_parity") or b_agg.get(
        "byte_exact_subset_parity"
    )
    b2b_saving = (b2b_eval or {}).get("global_token_saving_rate") or b_agg.get(
        "global_token_saving_rate"
    )

    out = {
        "schema": "nextgen_hybrid_b2b_design_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "design_spec": _rel(DESIGN_SPEC),
        "guarded_b2b": {
            "pointer": _rel(GUARDED_OUT),
            "contract_met": contract_met,
            "byte_exact_subset_parity": guarded_byte,
            "decode_contract_ko": guarded.get("decode_contract_ko"),
        },
        "hybrid_keep_ratio_sweep": sweep_arms,
        "hybrid_golden40_sweep_pointer": _rel(HYBRID_SWEEP_OUT),
        "hybrid_golden40_arms": [
            {
                "arm_id": a.get("arm_id"),
                "keep_ratio": a.get("keep_ratio"),
                "byte_exact_subset_parity": (a.get("aggregate") or {}).get(
                    "byte_exact_subset_parity"
                ),
                "spine_saving": (a.get("aggregate") or {}).get(
                    "global_token_saving_rate_spine_only"
                ),
            }
            for a in (hybrid_sweep.get("arms") or [])
        ],
        "b2b_domain_mkvs": {
            "domain_tag": args.b2b_domain,
            "bench_input": _rel(B2B_BENCH) if B2B_BENCH.is_file() else None,
            "eval_pointer": _rel(B2B_EVAL_OUT) if b2b_eval else None,
            "byte_exact_subset_parity": b2b_byte,
            "global_token_saving_rate": b2b_saving,
            "promotion_class": "research_only_arm",
        },
        "steps": steps,
        "design_verdict": {
            "b2b_decode_contract_ok": contract_met,
            "hybrid_byte_exact_on_golden40": all(
                (a.get("byte_exact_subset_parity") or 0) >= 1.0 for a in sweep_arms
            ),
            "active_apply_recommended": False,
            "note_ko": "B2B 내러티브=spine/MKVS 무손실; sidecar·latent는 NON_GATING·증거만",
        },
        "forbidden": [
            "latent-only recon as B2B official output",
            "longform/b2b MKVS as Track A ACTIVE headline without human gates",
        ],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "contract_met": contract_met,
                "b2b_byte_exact": b2b_byte,
                "b2b_saving": b2b_saving,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
