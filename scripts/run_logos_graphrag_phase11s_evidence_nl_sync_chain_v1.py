#!/usr/bin/env python3
"""Phase 11-S: HF gloss-stub A/B + evidence pack refresh + NL sandbox push [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11s_evidence_nl_sync_chain_v1_latest.json"
EVIDENCE = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"
HF_STUB = ROOT / "reports/deepnsm_hf_ab_research_stub_v1_latest.json"
PUSH_OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"


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
    ap.add_argument("--skip-hf-chain", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-nl-push", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_hf_chain:
        steps.append(_run("deepnsm_hf_explication", [PY, "scripts/run_deepnsm_hf_explication_chain_v1.py"]))
        steps.append(_run("deepnsm_hf_ab_stub", [PY, "scripts/build_deepnsm_hf_ab_research_stub_v1.py"]))

    if not args.skip_evidence_pack:
        steps.append(_run("build_evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))
        steps.append(_run("phase11h_chain", [PY, "scripts/run_logos_graphrag_phase11h_evidence_pack_chain_v1.py", "--skip-pytest"]))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec_enforce", [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"]))

    steps.append(_run("build_nl_research_pack", [PY, "scripts/build_notebooklm_universal_root_research_pack_v1.py"]))

    if not args.skip_nl_push:
        steps.append(_run("push_nl_research_pack", [PY, "scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py"], optional=True))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_evidence_pack",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_logos_graphrag_bridge_evidence_pack_v1.py::test_build_logos_graphrag_bridge_evidence_pack_v1",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    evidence_doc = _read_json(EVIDENCE)
    hf_doc = _read_json(HF_STUB)
    push_doc = _read_json(PUSH_OUT)
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}
    phase11 = (evidence_doc.get("phase_coverage") or {}).get("phase_11_universal_root_layer_stack") or {}

    push_ok = bool(push_doc.get("all_ok")) if not args.skip_nl_push else True
    all_ok = all(s.get("ok") for s in steps if s.get("label") != "push_nl_research_pack") and push_ok

    report = {
        "schema": "logos_graphrag_phase11s_evidence_nl_sync_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
        "deepnsm_hf_ab": {
            "ab_status": hf_doc.get("ab_status"),
            "comparison_ready": hf_doc.get("comparison_ready"),
            "delta_hf_minus_gematria": hf_doc.get("delta_hf_minus_gematria"),
        },
        "evidence_pack_phase": (phase11.get("gate_spec") or {}).get("phase"),
        "nl_push_ok_count": push_doc.get("ok_count"),
        "nl_push_all_ok": push_doc.get("all_ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11s_evidence_nl_sync_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "ab_status": hf_doc.get("ab_status"),
                "nl_push_ok": push_doc.get("ok_count"),
                "gate_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
