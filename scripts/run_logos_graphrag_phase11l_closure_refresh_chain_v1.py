#!/usr/bin/env python3
"""Phase 11-L: Phase12+ closure re-run + GATE_SPEC + sweep + public smoke [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11l_closure_refresh_chain_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json"
SWEEP = ROOT / "docs/final/artifacts/logos_phase14_full_sweep_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-closure-pytest", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-sweep", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-public-smoke", action="store_true")
    ap.add_argument("--deploy-assets", action="store_true", help="Pass -DeployAssets to Op30 Phase2 daily smoke")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(
        _run("commercial_readiness", [PY, "scripts/build_logos_observatory_commercial_readiness_v1.py"])
    )
    steps.append(_run("phase12_live_bundle", [PY, "scripts/build_logos_phase12_live_bundle_v1.py"]))
    steps.append(_run("magic_orb_probe", [PY, "scripts/probe_mkmlife_magic_orb_live_v1.py"], optional=True))

    closure_cmd = [PY, "scripts/build_logos_100pct_closure_v1.py", "--strict"]
    if not args.skip_closure_pytest:
        closure_cmd.append("--run-pytest")
    steps.append(_run("closure_100pct", closure_cmd))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))

    if not args.skip_sweep:
        steps.append(_run("phase14_sweep_report", [PY, "scripts/build_logos_phase14_full_sweep_report_v1.py"]))

    if not args.skip_evidence_pack:
        steps.append(_run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_public_smoke:
        smoke_cmd = [
            PY,
            "scripts/athena_run_v1.py",
            "--",
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/Invoke-Op30Phase2Daily_v1.ps1",
            "-SkipKvSync",
            "-SkipPostDeploySmoke",
            "-IncludeTierMatrixSmoke",
            "-IncludeOraclePreviewSmoke",
        ]
        if args.deploy_assets:
            smoke_cmd.append("-DeployAssets")
        steps.append(_run("op30_public_smoke", smoke_cmd, optional=True))

    closure_doc = _read_json(CLOSURE)
    sweep_doc = _read_json(SWEEP)
    gate_doc = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    op30_doc = _read_json(ROOT / "reports/op30_phase2_daily_latest.json")
    smoke_step = next((s for s in steps if s.get("label") == "op30_public_smoke"), {})

    core_labels = {"op30_public_smoke"}
    core_ok = all(s.get("ok") for s in steps if s.get("label") not in core_labels)
    closure_ok = bool(closure_doc.get("closure_ok"))
    all_ok = core_ok and closure_ok

    report = {
        "schema": "logos_graphrag_phase11l_closure_refresh_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "closure_ok": closure_ok,
        "closure_checks_passed": {
            k: v.get("passed")
            for k, v in (closure_doc.get("checks") or {}).items()
            if isinstance(v, dict)
        },
        "sweep_ok": sweep_doc.get("sweep_ok"),
        "gate_schema_ok": gate_doc.get("schema_validation_ok"),
        "all_enabled_planes_ok": (gate_doc.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "public_smoke_attempted": not args.skip_public_smoke,
        "deploy_assets": args.deploy_assets,
        "tier_matrix_smoke_ok": op30_doc.get("tier_matrix_smoke_ok"),
        "oracle_preview_smoke_ok": op30_doc.get("oracle_preview_smoke_ok"),
        "public_smoke_step_ok": smoke_step.get("ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11l_closure_refresh_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "closure_ok": closure_ok,
                "tier_matrix_smoke_ok": op30_doc.get("tier_matrix_smoke_ok"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
