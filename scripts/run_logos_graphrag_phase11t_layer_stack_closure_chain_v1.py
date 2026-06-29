#!/usr/bin/env python3
"""Phase 11-T: Universal Root layer stack closure signoff + pytest bundle [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11t_layer_stack_closure_chain_v1_latest.json"
CLOSURE = ROOT / "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json"


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
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-closure", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-nl-push", action="store_true")
    ap.add_argument("--relaxed-closure", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_gate_spec:
        steps.append(
            _run(
                "check_gate_spec_enforce",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    if not args.skip_closure:
        closure_cmd = [PY, "scripts/build_universal_root_layer_stack_closure_v1.py", "--enforce"]
        if args.relaxed_closure:
            closure_cmd.append("--relaxed")
        steps.append(_run("build_layer_stack_closure", closure_cmd))

    if not args.skip_pytest:
        pytest_targets = [
            "tests/test_check_universal_root_gate_spec_v1.py",
            "tests/test_universal_root_mdl_prune_poc_v1.py",
            "tests/test_build_universal_root_research_impl_bridge_v1.py",
            "tests/test_logos_graphrag_bridge_evidence_pack_v1.py::test_build_logos_graphrag_bridge_evidence_pack_v1",
        ]
        steps.append(
            _run(
                "pytest_universal_root_bundle",
                [PY, "-m", "pytest", *pytest_targets, "-q", "--tb=short"],
            )
        )
        steps.append(
            _run(
                "pytest_deepnsm_shadow_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_deepnsm_shadow_explication_v1.py::test_normalize_latin_translit_macrons",
                    "tests/test_deepnsm_shadow_explication_v1.py::test_normalize_script_form_strips_accents",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))

    steps.append(_run("build_nl_research_pack", [PY, "scripts/build_notebooklm_universal_root_research_pack_v1.py"]))

    if not args.skip_nl_push:
        steps.append(
            _run("push_nl_research_pack", [PY, "scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py"], optional=True)
        )

    closure_doc = _read_json(CLOSURE)
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    push_doc = _read_json(ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json")

    closure_ok = bool(closure_doc.get("closure_ok"))
    all_ok = all(s.get("ok") for s in steps if s.get("label") != "push_nl_research_pack") and closure_ok

    report = {
        "schema": "logos_graphrag_phase11t_layer_stack_closure_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "closure_ok": closure_ok,
        "closure_checks": closure_doc.get("checks"),
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "research_ready_decision": ev.get("research_ready_decision"),
        "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
        "enabled_plane_count": closure_doc.get("enabled_plane_count"),
        "nl_push_ok_count": push_doc.get("ok_count"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11t_layer_stack_closure_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "closure_ok": closure_ok,
                "gate_phase": report["gate_spec_phase"],
                "enabled_planes": report["enabled_plane_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
