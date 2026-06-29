#!/usr/bin/env python3
"""[HYPO] Phase 4: tri-lane bundle (patrol probe + NG arms merge) — research SSOT one JSON."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_tri_lane_research_bundle_v1_latest.json"
)
BLS_PROBE = ROOT / "reports/bls_unemployment_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_py(script: str, extra: list[str] | None = None) -> int:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.stdout.strip():
        print(cp.stdout.strip())
    if cp.stderr.strip():
        print(cp.stderr.strip(), file=sys.stderr)
    return int(cp.returncode)


def _lane_summary(
    *,
    lane_id: str,
    byte_parity: float | None,
    saving: float | None,
    jaccard: float | None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "lane_id": lane_id,
        "raw": {
            "byte_exact_subset_parity": byte_parity,
            "global_token_saving_rate": saving,
            "avg_reconstruction_fidelity_jaccard": jaccard,
        },
        "repair_v2": None,
    }
    if extra:
        row.update(extra)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Run probe, patrol, dual harness, phase3, guarded b2b (no BLS resolve)",
    )
    args = ap.parse_args()
    steps: list[dict[str, Any]] = []

    if args.execute:
        steps.append({"step": "bls_probe", "exit_code": _run_py("scripts/probe_bls_unemployment_may2026_v1.py")})
        rc_patrol = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts/run_general_prophecy_pre_june10_patrol_v1.ps1"),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        ).returncode
        steps.append({"step": "patrol", "exit_code": rc_patrol})
        steps.append(
            {
                "step": "dual_kpi_harness",
                "exit_code": _run_py("scripts/run_nextgen_dual_kpi_harness_v1.py"),
            }
        )
        steps.append(
            {
                "step": "phase3_mask",
                "exit_code": _run_py("scripts/run_nextgen_phase3_archetype_prior_chain_v1.py"),
            }
        )
        steps.append(
            {
                "step": "science_trilane_chain",
                "exit_code": _run_py("scripts/run_nextgen_science_prior_sidecar_chain_v1.py"),
            }
        )
        steps.append(
            {
                "step": "guarded_b2b",
                "exit_code": _run_py("scripts/run_nextgen_guarded_b2b_decode_contract_v1.py"),
            }
        )

    bls = _load(BLS_PROBE)
    dual = _load(
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_dual_kpi_harness_v1_latest.json"
    )
    phase3 = _load(
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_archetype_prior_mask_v1_latest.json"
    )
    guarded = _load(
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
    )
    logos = _load(
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
    )
    science_chain = _load(
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_science_prior_sidecar_chain_v1_latest.json"
    )
    lut = _load(
        ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
    )

    lanes: list[dict[str, Any]] = []
    if dual:
        for arm in dual.get("arms_summary") or []:
            r = arm.get("raw") or {}
            lanes.append(
                _lane_summary(
                    lane_id=str(arm.get("arm_id")),
                    byte_parity=r.get("byte_exact_subset_parity"),
                    saving=r.get("global_token_saving_rate"),
                    jaccard=r.get("avg_reconstruction_fidelity_jaccard"),
                    extra={"pareto_status": arm.get("pareto_status"), "lane": arm.get("lane")},
                )
            )
    if phase3:
        agg = phase3.get("aggregate") or {}
        be = phase3.get("byte_exact_subset") or {}
        lanes.append(
            _lane_summary(
                lane_id="phase3_archetype_prior_must_keep",
                byte_parity=be.get("byte_exact_subset_parity"),
                saving=agg.get("global_token_saving_rate"),
                jaccard=agg.get("avg_reconstruction_fidelity_jaccard"),
                extra={"policy_mask_only": phase3.get("policy_mask_only")},
            )
        )
    if guarded:
        agg = guarded.get("aggregate") or {}
        lanes.append(
            _lane_summary(
                lane_id="guarded_b2b_spine_official_recon",
                byte_parity=agg.get("byte_exact_subset_parity"),
                saving=agg.get("global_token_saving_rate_spine_storage"),
                jaccard=agg.get("avg_b2b_recon_jaccard"),
                extra={
                    "contract_met": agg.get("contract_met"),
                    "avg_sidecar_preview_jaccard": agg.get("avg_sidecar_preview_jaccard"),
                },
            )
        )
    if logos:
        agg = logos.get("aggregate") or {}
        lanes.append(
            _lane_summary(
                lane_id="hybrid_spine_logos_sidecar",
                byte_parity=agg.get("byte_exact_subset_parity"),
                saving=agg.get("global_token_saving_rate_spine_plus_logos_sidecar"),
                jaccard=agg.get("avg_reconstruction_fidelity_jaccard"),
                extra={"salience_hook_wired": logos.get("salience_hook_wired")},
            )
        )
    if science_chain:
        raw_sc = science_chain.get("raw") or {}
        th = raw_sc.get("trilane_hybrid") or {}
        p3 = raw_sc.get("phase3_ng40_mask") or {}
        lanes.append(
            _lane_summary(
                lane_id="science_trilane_sidecar_chain",
                byte_parity=th.get("byte_exact_subset_parity"),
                saving=p3.get("global_token_saving_rate"),
                jaccard=p3.get("avg_reconstruction_fidelity_jaccard"),
                extra={
                    "closure_ok": science_chain.get("closure_ok"),
                    "delta_vs_archetype": (science_chain.get("delta") or {}).get(
                        "vs_archetype_only_phase3"
                    ),
                },
            )
        )

    b2b_ready = bool(guarded and (guarded.get("aggregate") or {}).get("contract_met"))
    out = {
        "schema": "nextgen_tri_lane_research_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "bls_macro": {
            "probe_pointer": "reports/bls_unemployment_probe_v1_latest.json",
            "status": (bls or {}).get("status"),
            "may_2026_release_ready": (bls or {}).get("may_2026_release_ready"),
            "resolve_skipped_unless_ready": True,
        },
        "lut_draft_pointer": "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json",
        "lut_human_signoff_required": (lut or {}).get("human_signoff_required", True),
        "lanes": lanes,
        "synthesis_ko": {
            "b2b_byte_exact_contract": "guarded_b2b_spine_official_recon arm only",
            "b2b_contract_met": b2b_ready,
            "latent_byte_exact": "phase3 + ng40_latent paths remain 0/40 until spine-hybrid product split",
            "promotion": "forbidden until commander signoff + dual-axis evidence",
        },
        "pareto_dual_axis": (dual or {}).get("pareto_synthesis"),
        "subprocess_steps": steps,
        "stub_pointer": (
            "experiments/nextgen_clean_slate_cpu_v1/"
            "SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "lane_count": len(lanes),
                "b2b_contract_met": b2b_ready,
                "bls_status": out["bls_macro"]["status"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
