#!/usr/bin/env python3
"""RQ-024 B-track chain: single holdout + multi-split + WF ablation + summary bundle."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PROJECT = ROOT / "docs/final/artifacts/rq024_btc_lens_feature_v0_project_v1.json"
DEFAULT_HOLDOUT = ROOT / "reports/rq024_btc_lens_feature_v0_blind_holdout_v1_latest.json"
DEFAULT_MULTISPLIT = ROOT / "reports/rq024_btc_lens_feature_v0_multisplit_v1_latest.json"
DEFAULT_WF = ROOT / "reports/rq024_btc_lens_feature_v0_wf_ablation_v1_latest.json"
DEFAULT_FLOW = ROOT / "reports/rq024_a_flow_sublane_summary_v1_latest.json"
DEFAULT_TRIANGLE = ROOT / "reports/rq024_btc_lens_v1_triangular_validation_v1_latest.json"
DEFAULT_STABILITY = ROOT / "reports/rq024_btc_lens_v1_wf_stability_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_feature_v0_chain_v1_latest.json"
SCHEMA = "rq024_btc_lens_feature_v0_chain_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, *extra: str) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-json", type=Path, default=DEFAULT_PROJECT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-multisplit", action="store_true")
    ap.add_argument("--skip-wf-ablation", action="store_true")
    ap.add_argument("--skip-flow-sublane", action="store_true")
    args = ap.parse_args(argv)

    project_path = args.project_json if args.project_json.is_absolute() else ROOT / args.project_json
    project = _load_json(project_path)

    steps: list[dict[str, Any]] = []
    scripts = [
        ("blind_holdout_v0", "run_rq024_btc_lens_feature_v0_blind_holdout_v1.py"),
    ]
    if not args.skip_multisplit:
        scripts.append(("multisplit_v1", "run_rq024_btc_lens_feature_v0_multisplit_v1.py"))
    if not args.skip_wf_ablation:
        scripts.append(("wf_ablation_v1", "run_rq024_btc_lens_feature_v0_wf_ablation_v1.py"))
    if not args.skip_flow_sublane:
        scripts.append(("flow_sublane_a", "build_rq024_a_flow_sublane_summary_v1.py"))
    scripts.append(("v1_wf_stability", "analyze_rq024_btc_lens_v1_wf_stability_v1.py"))
    scripts.append(("v1_triangular", "build_rq024_btc_lens_v1_triangular_validation_v1.py"))

    exit_codes: list[int] = []
    for step_name, script in scripts:
        rc, log = _run_py(script)
        exit_codes.append(rc)
        steps.append(
            {
                "step": step_name,
                "script": script,
                "exit_code": rc,
                "output_tail": log.splitlines()[-6:] if log else [],
            }
        )

    holdout = _load_json(DEFAULT_HOLDOUT)
    multisplit = _load_json(DEFAULT_MULTISPLIT)
    wf = _load_json(DEFAULT_WF)
    flow = _load_json(DEFAULT_FLOW)
    triangle = _load_json(DEFAULT_TRIANGLE)
    stability = _load_json(DEFAULT_STABILITY)

    wf_dod = wf.get("dod_wf_ablation") or {}
    v1_wf_pass = bool(wf_dod.get("best_v1_mean_beats_052"))
    v0_wf_pass = bool(wf_dod.get("best_v0_mean_beats_052"))
    multisplit_met = bool((multisplit.get("dod_multisplit") or {}).get("met"))
    multisplit_v1_met = bool((multisplit.get("dod_multisplit_v1") or {}).get("met"))

    final_action = triangle.get("final_action") or "WATCH"
    if not triangle:
        if multisplit_met and (v1_wf_pass or v0_wf_pass):
            final_action = "WATCH_STRENGTHENED"
        if v1_wf_pass and not v0_wf_pass:
            final_action = "WATCH_V1_WF"

    bundle = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "project_json": str(project_path.relative_to(ROOT)).replace("\\", "/")
        if project_path.is_relative_to(ROOT)
        else str(project_path),
        "project_status": project.get("status"),
        "steps": steps,
        "holdout_summary": holdout.get("comparison"),
        "dod_v0_single": holdout.get("dod_v0"),
        "multisplit_summary": multisplit.get("aggregate"),
        "dod_multisplit": multisplit.get("dod_multisplit"),
        "dod_multisplit_v1": multisplit.get("dod_multisplit_v1"),
        "dod_v1_single": holdout.get("dod_v1"),
        "wf_ablation_summary": {
            "best_v0_by_mean": (wf.get("best_v0_by_mean_test_accuracy") or {}).get("v0_aggregate"),
            "best_v1_by_mean": (wf.get("best_v1_by_mean_test_accuracy") or {}).get("v1_aggregate"),
            "overall_v0_mean": wf.get("overall_v0_mean_across_nf_configs"),
            "overall_v1_mean": wf.get("overall_v1_mean_across_nf_configs"),
            "dod_wf_ablation": wf_dod,
        },
        "flow_sublane_a_summary": flow.get("probe"),
        "v1_wf_stability": {
            "weak_nf_configs": stability.get("weak_nf_configs"),
            "strong_nf_configs": stability.get("strong_nf_configs"),
            "best_v1_nf": stability.get("best_v1_nf"),
        },
        "v1_triangular_validation": triangle.get("triangle"),
        "final_action": final_action,
        "chain_ok": all(c == 0 for c in exit_codes),
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"chain_ok={bundle['chain_ok']} final_action={final_action} "
        f"triangle={(triangle.get('triangle') or {}).get('met')} v1_multisplit={multisplit_v1_met}"
    )
    return 0 if bundle["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
