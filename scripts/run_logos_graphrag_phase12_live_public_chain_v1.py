#!/usr/bin/env python3
"""Phase 12: Logos live bundle + showroom public smoke + optional OP30 tier [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase12_live_public_chain_v1_latest.json"
LIVE_BUNDLE = ROOT / "reports/logos_phase12_live_bundle_v1_latest.json"
SHOWROOM = ROOT / "reports/showroom_trust_viz_public_chain_smoke_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json"
READINESS = ROOT / "reports/logos_observatory_commercial_readiness_v1_latest.json"
OP30 = ROOT / "reports/op30_phase2_daily_latest.json"


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
    ap.add_argument("--skip-commercial", action="store_true")
    ap.add_argument("--skip-showroom", action="store_true")
    ap.add_argument("--skip-live-bundle", action="store_true")
    ap.add_argument("--skip-load-probe", action="store_true")
    ap.add_argument("--skip-op30-smoke", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-nl-push", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_commercial:
        steps.append(_run("commercial_readiness", [PY, "scripts/build_logos_observatory_commercial_readiness_v1.py"]))

    if not args.skip_showroom:
        steps.append(_run("showroom_trust_viz_smoke", [PY, "scripts/check_showroom_trust_viz_public_chain_v1.py"]))

    if not args.skip_live_bundle:
        steps.append(_run("phase12_live_bundle", [PY, "scripts/build_logos_phase12_live_bundle_v1.py"]))

    if not args.skip_load_probe:
        steps.append(
            _run(
                "showroom_static_load_probe",
                [PY, "scripts/build_showroom_static_load_probe_v1.py", "--requests-per-url", "3", "--workers", "4"],
                optional=True,
            )
        )

    if not args.skip_op30_smoke:
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
        steps.append(_run("op30_public_smoke", smoke_cmd, optional=True))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(
            _run(
                "check_gate_spec_enforce",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    steps.append(_run("build_nl_research_pack", [PY, "scripts/build_notebooklm_universal_root_research_pack_v1.py"]))

    if not args.skip_nl_push:
        steps.append(
            _run("push_nl_research_pack", [PY, "scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py"], optional=True)
        )

    live_doc = _read_json(LIVE_BUNDLE)
    showroom_doc = _read_json(SHOWROOM)
    closure_doc = _read_json(CLOSURE)
    readiness_doc = _read_json(READINESS)
    op30_doc = _read_json(OP30)
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}
    smoke_step = next((s for s in steps if s.get("label") == "op30_public_smoke"), {})

    live_ok = bool(live_doc.get("ok")) and bool(live_doc.get("jemaai_core_ok"))
    showroom_ok = bool(showroom_doc.get("ok"))
    closure_ok = bool(closure_doc.get("closure_ok"))
    core_ok = all(
        s.get("ok")
        for s in steps
        if s.get("label") not in {"op30_public_smoke", "showroom_static_load_probe", "push_nl_research_pack"}
    )
    all_ok = core_ok and live_ok and showroom_ok and closure_ok

    report = {
        "schema": "logos_graphrag_phase12_live_public_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "phase12_live": {
            "live_bundle_ok": live_doc.get("ok"),
            "jemaai_core_ok": live_doc.get("jemaai_core_ok"),
            "mkmlife_public_schema_ok": live_doc.get("mkmlife_public_schema_ok"),
            "local_mkmlife_present": (live_doc.get("local_mkmlife_copy") or {}).get("present"),
            "errors": live_doc.get("errors"),
        },
        "showroom_public_smoke_ok": showroom_ok,
        "layer_stack_closure_ok": closure_ok,
        "commercial_stack_ok": readiness_doc.get("commercial_stack_ok"),
        "op30_smoke": {
            "attempted": not args.skip_op30_smoke,
            "step_ok": smoke_step.get("ok"),
            "tier_matrix_smoke_ok": op30_doc.get("tier_matrix_smoke_ok"),
            "oracle_preview_smoke_ok": op30_doc.get("oracle_preview_smoke_ok"),
        },
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase12_live_public_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "live_ok": live_ok,
                "showroom_ok": showroom_ok,
                "gate_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
