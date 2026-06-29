#!/usr/bin/env python3
"""Phase 13: DeepNSM HF Ollama local-weights pilot + Phase 12 carry + evidence/NL [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1_latest.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_100_v1.json"
HF_OLLAMA_CHAIN = ROOT / "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
PHASE12 = ROOT / "reports/logos_graphrag_phase12_live_public_chain_v1_latest.json"
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
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--max-pairs", type=int, default=0, help="0 = all pairs in pilot fixture")
    ap.add_argument("--skip-ollama", action="store_true", help="Use gloss_stub only (no phase-13 signoff)")
    ap.add_argument("--skip-phase12-verify", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-nl-push", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_phase12_verify:
        steps.append(
            _run(
                "phase12_carry_verify",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    hf_cmd = [
        PY,
        "scripts/run_deepnsm_hf_explication_chain_v1.py",
        "--backend",
        "ollama" if not args.skip_ollama else "gloss_stub",
        "--fixture",
        str(args.fixture),
        "--out",
        "docs/final/artifacts/deepnsm_hf_explication_ollama_v1.jsonl",
        "--report",
        "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json",
        "--audit-out",
        "reports/nsm_41k_lexicon_crosswalk_audit_hf_ollama_v1_latest.json",
    ]
    if args.max_pairs > 0:
        hf_cmd.extend(["--max-pairs", str(args.max_pairs)])
    if args.skip_ollama:
        hf_cmd.append("--skip-ollama-fallback")

    steps.append(_run("deepnsm_hf_ollama_explication", hf_cmd))
    steps.append(_run("deepnsm_hf_ab_refresh", [PY, "scripts/build_deepnsm_hf_ab_research_stub_v1.py"]))

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
            _run(
                "push_nl_research_pack",
                [PY, "scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py"],
                optional=True,
            )
        )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_deepnsm_ollama_smoke",
                [PY, "-m", "pytest", "tests/test_deepnsm_hf_ollama_inference_v1.py", "-q", "--tb=short"],
            )
        )

    hf_chain = _read_json(HF_OLLAMA_CHAIN)
    hf_ab = _read_json(ROOT / "reports/deepnsm_hf_ab_research_stub_v1_latest.json")
    phase12 = _read_json(PHASE12)
    closure = _read_json(CLOSURE)
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}

    impl = hf_chain.get("implementation_status")
    ollama_ok = impl == "ollama_local_weights_v1" and bool(hf_chain.get("ok"))
    phase12_ok = bool(phase12.get("all_ok"))
    closure_ok = bool(closure.get("closure_ok"))
    core_ok = all(
        s.get("ok")
        for s in steps
        if s.get("label") not in {"push_nl_research_pack"}
    )
    all_ok = core_ok and ollama_ok and phase12_ok and closure_ok and bool(ev.get("all_enabled_planes_ok"))

    report = {
        "schema": "logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "ollama_mode": "skipped" if args.skip_ollama else "live",
        "pilot_fixture": str(args.fixture.relative_to(ROOT)).replace("\\", "/"),
        "phase12_carry_ok": phase12_ok,
        "layer_stack_closure_ok": closure_ok,
        "deepnsm_hf_ollama": {
            "implementation_status": impl,
            "pair_count": hf_chain.get("pair_count"),
            "ollama_model": (hf_chain.get("ollama_meta") or {}).get("ollama_model"),
            "hf_audit": hf_chain.get("hf_ollama_audit") or hf_chain.get("hf_stub_audit"),
            "delta_hf_minus_gematria": hf_chain.get("delta_hf_ollama_minus_gematria")
            or hf_chain.get("delta_hf_stub_minus_gematria"),
            "ab_status": hf_ab.get("ab_status"),
        },
        "gate_eval_summary": {
            "research_ready_decision": ev.get("research_ready_decision"),
            "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
        },
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "implementation_status": impl,
                "gate_spec_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
