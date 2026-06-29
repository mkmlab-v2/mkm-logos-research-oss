#!/usr/bin/env python3
"""Phase 11-R: cost plane enable + DeepNSM HF A/B research stub + GATE_SPEC refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1_latest.json"
STRESS_GAP = ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"
HF_STUB = ROOT / "reports/deepnsm_hf_ab_research_stub_v1_latest.json"


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
    ap.add_argument("--skip-shallow-stress", action="store_true")
    ap.add_argument("--skip-hf-stub", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-nl-pack", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_shallow_stress:
        steps.append(
            _run(
                "shallow_stress_11g",
                [PY, "scripts/run_logos_graphrag_phase11g_shallow_stress_chain_v1.py", "--skip-pytest"],
                optional=True,
            )
        )

    if not args.skip_hf_stub:
        steps.append(_run("deepnsm_hf_ab_stub", [PY, "scripts/build_deepnsm_hf_ab_research_stub_v1.py"]))
        steps.append(
            _run(
                "deepnsm_shadow_distortion_refresh",
                [PY, "scripts/run_deepnsm_shadow_distortion_chain_v1.py"],
                optional=True,
            )
        )

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
        steps.append(
            _run(
                "check_gate_spec_enforce",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    if not args.skip_evidence_pack:
        steps.append(
            _run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"], optional=True)
        )

    if not args.skip_nl_pack:
        steps.append(_run("build_nl_pack", [PY, "scripts/build_notebooklm_universal_root_research_pack_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_gate_spec",
                [PY, "-m", "pytest", "tests/test_check_universal_root_gate_spec_v1.py", "-q", "--tb=short"],
            )
        )

    stress = _read_json(STRESS_GAP)
    stress_raw = stress.get("raw") or {}
    hf_stub = _read_json(HF_STUB)
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    planes = ((spec.get("promotion_gates") or {}).get("planes") or {})
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}

    cost_enabled = bool((planes.get("cost") or {}).get("enabled"))
    cloud_skip = stress_raw.get("cloud_skip_ratio")
    core_ok = all(s.get("ok") for s in steps if s.get("label") != "shallow_stress_11g")
    all_ok = core_ok and cost_enabled and bool(hf_stub.get("arms"))

    report = {
        "schema": "logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "cost_plane": {
            "enabled_in_spec": cost_enabled,
            "cloud_skip_ratio": cloud_skip,
            "routing_oracle_gap": stress_raw.get("routing_oracle_gap"),
            "fixtures_evaluated": stress.get("fixtures_evaluated"),
            "scope_note": "shallow preprocess fixture only — not OS-wide CSR",
        },
        "deepnsm_hf_ab": {
            "ab_status": hf_stub.get("ab_status"),
            "comparison_ready": hf_stub.get("comparison_ready"),
            "gematria_gate_ok": (
                (hf_stub.get("arms") or {}).get("gematria_shadow", {}).get("distortion_metrics") or {}
            ).get("gate_ok"),
            "hf_implementation_status": (
                (hf_stub.get("arms") or {}).get("deepnsm_hf_1b", {}).get("implementation_status")
            ),
        },
        "gate_eval_summary": {
            "research_ready_decision": ev.get("research_ready_decision"),
            "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
            "enabled_plane_count": sum(1 for p in (ev.get("planes") or []) if p.get("enabled")),
            "planes": [
                {"plane": p.get("plane"), "enabled": p.get("enabled"), "ok": p.get("ok")}
                for p in (ev.get("planes") or [])
            ],
        },
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "cost_enabled": cost_enabled,
                "cloud_skip_ratio": cloud_skip,
                "all_planes_ok": ev.get("all_enabled_planes_ok"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
