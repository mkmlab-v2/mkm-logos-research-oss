#!/usr/bin/env python3
"""Phase 11-K: sidecar ablation v3 (retrieve+distortion) + GATE_SPEC + evidence pack [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11k_sidecar_ablation_v3_chain_v1_latest.json"
V3_OUT = ROOT / "reports/universal_root_sidecar_ablation_v3_latest.json"


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
    ap.add_argument("--skip-v2", action="store_true")
    ap.add_argument("--skip-distortion", action="store_true")
    ap.add_argument("--quick-v2", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-mkmlife-deploy", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    v3_cmd = [PY, "scripts/run_universal_root_sidecar_ablation_v3_chain_v1.py"]
    if args.skip_v2:
        v3_cmd.append("--skip-v2")
    if args.skip_distortion:
        v3_cmd.append("--skip-distortion")
    if args.quick_v2:
        v3_cmd.append("--quick-v2")
    steps.append(_run("sidecar_ablation_v3", v3_cmd))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_mkmlife_deploy:
        deploy_cmd = [
            PY,
            "scripts/athena_run_v1.py",
            "--",
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/Invoke-Op30Phase2Daily_v1.ps1",
            "-DeployAssets",
            "-SkipKvSync",
            "-SkipPostDeploySmoke",
        ]
        steps.append(_run("mkmlife_deploy_assets", deploy_cmd, optional=True))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_ablation_v3_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_run_universal_root_sidecar_ablation_v3_chain_v1.py",
                    "-q",
                    "--tb=short",
                ],
                optional=True,
            )
        )

    v3_doc = _read_json(V3_OUT)
    gate_doc = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    op30_doc = _read_json(ROOT / "reports/op30_phase2_daily_latest.json")
    deploy_step = next((s for s in steps if s.get("label") == "mkmlife_deploy_assets"), {})
    deploy_ok = deploy_step.get("ok") if deploy_step else None
    planes = v3_doc.get("planes") if isinstance(v3_doc.get("planes"), dict) else {}

    core_ok = all(
        s.get("ok")
        for s in steps
        if s.get("label") not in ("mkmlife_deploy_assets", "pytest_ablation_v3_smoke")
    )
    all_ok = core_ok and bool(v3_doc.get("all_ok"))

    report = {
        "schema": "logos_graphrag_phase11k_sidecar_ablation_v3_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "sidecar_ablation_v3_ok": v3_doc.get("all_ok"),
        "retrieve_plane_ok": (planes.get("retrieve_sidecar_v2") or {}).get("ok"),
        "distortion_ok": planes.get("distortion_ok"),
        "distortion_delta": planes.get("distortion_delta_shadow_minus_raw"),
        "gate_schema_ok": gate_doc.get("schema_validation_ok"),
        "all_enabled_planes_ok": (gate_doc.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "mkmlife_deploy_attempted": not args.skip_mkmlife_deploy,
        "mkmlife_deploy_ok": deploy_ok,
        "op30_failed_steps": op30_doc.get("failed_steps") if op30_doc else None,
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11k_sidecar_ablation_v3_chain_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "v3_ok": v3_doc.get("all_ok"),
                "mkmlife_deploy_ok": deploy_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
