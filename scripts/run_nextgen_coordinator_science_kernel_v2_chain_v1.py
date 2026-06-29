#!/usr/bin/env python3
"""[HYPO] Coordinator science kernel v2: bounded loss sweep + thin prophecy feature binding."""
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
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_science_kernel_v2_chain_v1_latest.json"
)
SWEEP_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_science_loss_sweep_v1_latest.json"
)
RECONCILE_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_coordinator_active_eval_axis_reconcile_v1_latest.json"
)
BIND_OUT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/coordinator_prophecy_feature_binding_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = ((cp.stdout or "") + (cp.stderr or "")).strip()[-1500:]
    return int(cp.returncode), tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--smoke", action="store_true", help="Small sweep grid only")
    ap.add_argument("--skip-prophecy-bind", action="store_true")
    ap.add_argument("--skip-reconcile", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    sweep_extra = ["--smoke"] if args.smoke else []
    rc, log = _run("scripts/run_nextgen_coordinator_science_loss_sweep_v1.py", sweep_extra)
    steps.append({"step": "coordinator_loss_sweep", "exit_code": rc, "log_tail": log})
    if rc != 0:
        _write(args.out_json, steps, None, None, None)
        return rc

    sweep_doc = json.loads(SWEEP_OUT.read_text(encoding="utf-8-sig"))
    bind_doc = None
    if not args.skip_prophecy_bind:
        rc2, log2 = _run("scripts/bind_coordinator_science_prophecy_features_v1.py")
        steps.append({"step": "prophecy_feature_binding", "exit_code": rc2, "log_tail": log2})
        if rc2 == 0 and BIND_OUT.is_file():
            bind_doc = json.loads(BIND_OUT.read_text(encoding="utf-8-sig"))

    reconcile_doc = None
    if not args.skip_reconcile:
        rc3, log3 = _run("scripts/run_nextgen_coordinator_active_eval_axis_reconcile_v1.py")
        steps.append({"step": "active_eval_axis_reconcile", "exit_code": rc3, "log_tail": log3})
        if rc3 != 0:
            _write(args.out_json, steps, sweep_doc, bind_doc, None)
            return rc3
        if RECONCILE_OUT.is_file():
            reconcile_doc = json.loads(RECONCILE_OUT.read_text(encoding="utf-8-sig"))

    manifest = _write(args.out_json, steps, sweep_doc, bind_doc, reconcile_doc)
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "closure_ok": manifest["closure_ok"],
                "dual_axis_beat": (manifest.get("raw") or {}).get("dual_axis_beat"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if manifest["closure_ok"] else 1


def _write(
    path: Path,
    steps: list[dict[str, Any]],
    sweep: dict[str, Any] | None,
    bind: dict[str, Any] | None,
    reconcile: dict[str, Any] | None,
) -> dict[str, Any]:
    closure_ok = all(s.get("exit_code") == 0 for s in steps)
    raw: dict[str, Any] = {}
    if sweep:
        raw["sweep_rows"] = sweep.get("row_count")
        raw["best_by_loss"] = sweep.get("best_by_loss")
        raw["best_dual_axis_beat"] = sweep.get("best_dual_axis_beat")
        raw["dual_axis_beat"] = bool(sweep.get("best_dual_axis_beat"))
    if bind:
        raw["prophecy_features"] = len(bind.get("proposed_features") or [])
    if reconcile:
        raw["axis_reconcile"] = reconcile.get("delta_hybrid_minus_active")
        raw["conflation_guard"] = reconcile.get("conflation_guard")

    manifest = {
        "schema": "nextgen_coordinator_science_kernel_v2_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "gating_policy": "NON_GATING",
        "closure_ok": closure_ok,
        "steps": steps,
        "pointers": {
            "kernel_spec": (
                "experiments/nextgen_clean_slate_cpu_v1/COORDINATOR_SCIENCE_KERNEL_V2.json"
            ),
            "sweep": str(SWEEP_OUT.relative_to(ROOT)).replace("\\", "/"),
            "prophecy_binding": str(BIND_OUT.relative_to(ROOT)).replace("\\", "/"),
            "axis_reconcile": str(RECONCILE_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "raw": raw,
        "repair_v2": None,
        "forbidden": [
            "overwrite_multilens_active_report",
            "merge_general_prophecy_l1_with_ng40_codec",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    raise SystemExit(main())
