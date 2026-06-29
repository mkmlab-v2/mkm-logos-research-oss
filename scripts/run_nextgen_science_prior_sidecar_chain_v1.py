#!/usr/bin/env python3
"""[HYPO] One-click: tri-lane hybrid stack + phase3 science prior mask (research sandbox)."""
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
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_science_prior_sidecar_chain_v1_latest.json"
)
TRILANE_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_trilane_stack_v1_latest.json"
)
PHASE3_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_science_prior_mask_v1_latest.json"
)
ARCHETYPE_PHASE3 = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_archetype_prior_mask_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_py(script: str, extra: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "") + (cp.stderr or "")
    return int(cp.returncode), tail.strip()[-2000:]


def _delta_vs_archetype(science_doc: dict[str, Any]) -> dict[str, Any]:
    arch = _load(ARCHETYPE_PHASE3)
    if not arch:
        return {"archetype_baseline_present": False}
    sa = science_doc.get("aggregate") or {}
    aa = arch.get("aggregate") or {}
    sj = float(sa.get("avg_reconstruction_fidelity_jaccard") or 0)
    aj = float(aa.get("avg_reconstruction_fidelity_jaccard") or 0)
    ss = float(sa.get("global_token_saving_rate") or 0)
    a_s = float(aa.get("global_token_saving_rate") or 0)
    return {
        "archetype_baseline_present": True,
        "jaccard_delta_trilane_minus_archetype_only": round(sj - aj, 6),
        "saving_delta_trilane_minus_archetype_only": round(ss - a_s, 6),
        "archetype_only_jaccard": aj,
        "archetype_only_saving": a_s,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument(
        "--science-only",
        action="store_true",
        help="Phase3/hybrid use science spec tokens only",
    )
    ap.add_argument(
        "--skip-phase3",
        action="store_true",
        help="Run hybrid trilane stack only (faster)",
    )
    args = ap.parse_args()

    extra = ["--science-only"] if args.science_only else []
    steps: list[dict[str, Any]] = []

    rc, log = _run_py("scripts/run_nextgen_hybrid_spine_trilane_stack_v1.py", extra)
    steps.append({"step": "hybrid_trilane_stack", "exit_code": rc, "log_tail": log})
    if rc != 0:
        _write_manifest(args.out_json, steps, None, None, args.science_only)
        return rc

    if not args.skip_phase3:
        rc2, log2 = _run_py("scripts/run_nextgen_phase3_science_prior_mask_v1.py", extra)
        steps.append({"step": "phase3_science_mask", "exit_code": rc2, "log_tail": log2})
        if rc2 != 0:
            _write_manifest(args.out_json, steps, _load(TRILANE_OUT), None, args.science_only)
            return rc2

    trilane = _load(TRILANE_OUT)
    phase3 = _load(PHASE3_OUT) if not args.skip_phase3 else None
    manifest = _write_manifest(
        args.out_json, steps, trilane, phase3, args.science_only
    )
    print(json.dumps({"wrote": str(args.out_json), "closure_ok": manifest.get("closure_ok")}))
    return 0 if manifest.get("closure_ok") else 1


def _write_manifest(
    out_path: Path,
    steps: list[dict[str, Any]],
    trilane: dict[str, Any] | None,
    phase3: dict[str, Any] | None,
    science_only: bool,
) -> dict[str, Any]:
    closure_ok = all(s.get("exit_code") == 0 for s in steps)
    delta = _delta_vs_archetype(phase3) if phase3 else {}
    manifest = {
        "schema": "nextgen_science_prior_sidecar_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "gating_policy": "NON_GATING",
        "science_only": science_only,
        "closure_ok": closure_ok,
        "steps": steps,
        "pointers": {
            "spec": "experiments/nextgen_clean_slate_cpu_v1/SCIENCE_PRIOR_SIDECAR_SPEC_V1.json",
            "trilane_stack": str(TRILANE_OUT.relative_to(ROOT)).replace("\\", "/"),
            "phase3_mask": str(PHASE3_OUT.relative_to(ROOT)).replace("\\", "/"),
            "stub": (
                "experiments/nextgen_clean_slate_cpu_v1/"
                "SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
            ),
        },
        "raw": {},
        "repair_v2": None,
        "delta": {
            "repair_v2_minus_raw": None,
            "vs_archetype_only_phase3": delta,
        },
        "forbidden": [
            "overwrite_multilens_active_report",
            "merge_general_prophecy_l1_with_ng40_codec",
            "track_a_promotion_without_human_signoff",
        ],
        "next_gates": [
            "beat_check vs frozen ACTIVE on phase3 aggregate",
            "optional prophecy AB: scripts/run_prophecy_btrack_recommended_eval_chain_v1.py",
        ],
    }
    if trilane:
        agg = trilane.get("aggregate") or {}
        manifest["raw"]["trilane_hybrid"] = {
            "byte_exact_subset_parity": agg.get("byte_exact_subset_parity"),
            "avg_trilane_sidecar_jaccard": agg.get("avg_trilane_sidecar_jaccard"),
            "combined_terms": (trilane.get("term_counts") or {}).get("combined"),
        }
    if phase3:
        agg = phase3.get("aggregate") or {}
        be = phase3.get("byte_exact_subset") or {}
        manifest["raw"]["phase3_ng40_mask"] = {
            "global_token_saving_rate": agg.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": agg.get(
                "avg_reconstruction_fidelity_jaccard"
            ),
            "byte_exact_subset_parity": be.get("byte_exact_subset_parity"),
            "prior_terms_count": phase3.get("prior_terms_count"),
        }
        bc = phase3.get("beat_check") or {}
        manifest["raw"]["beat_check"] = bc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    raise SystemExit(main())
