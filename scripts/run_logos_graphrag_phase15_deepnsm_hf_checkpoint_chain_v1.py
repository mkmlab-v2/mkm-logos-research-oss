#!/usr/bin/env python3
"""Phase 15: DeepNSM HF 1B checkpoint pilot + Ollama vs checkpoint A/B [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1_latest.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_100_v1.json"
HF_CHECKPOINT_CHAIN = ROOT / "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json"
PHASE14 = ROOT / "reports/logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1_latest.json"
OLLAMA_VS_CKPT = ROOT / "reports/deepnsm_hf_ollama_vs_checkpoint_ab_v1_latest.json"


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


def _rel(p: Path) -> str:
    try:
        path = p if p.is_absolute() else (ROOT / p)
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--max-pairs", type=int, default=0)
    ap.add_argument("--skip-explication", action="store_true")
    ap.add_argument("--skip-carry-verify", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-nl-push", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_carry_verify:
        steps.append(
            _run(
                "gate_spec_enforce_carry",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    steps.append(_run("checkpoint_prereqs", [PY, "scripts/check_deepnsm_hf_checkpoint_prereqs_v1.py"], optional=True))
    prereqs = _read_json(ROOT / "reports/deepnsm_hf_checkpoint_prereqs_v1_latest.json")
    llama_gate_ok = bool((prereqs.get("checks") or {}).get("llama_base_gate", {}).get("ok"))
    checkpoint_ready = bool(prereqs.get("ok"))

    hf_cmd = [
        PY,
        "scripts/run_deepnsm_hf_explication_chain_v1.py",
        "--backend",
        "hf_checkpoint",
        "--fixture",
        str(args.fixture),
        "--out",
        "docs/final/artifacts/deepnsm_hf_explication_checkpoint_v1.jsonl",
        "--report",
        "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json",
        "--audit-out",
        "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json",
    ]
    if args.max_pairs > 0:
        hf_cmd.extend(["--max-pairs", str(args.max_pairs)])

    if not args.skip_explication and llama_gate_ok:
        steps.append(_run("deepnsm_hf_checkpoint_explication", hf_cmd))
    else:
        steps.append(
            {
                "label": "deepnsm_hf_checkpoint_explication",
                "cmd": ["skipped"],
                "exit_code": 0,
                "ok": True,
                "tail": "skip_explication"
                if args.skip_explication
                else "blocked_gated_llama_base",
            }
        )

    if llama_gate_ok:
        steps.append(
            _run("ollama_vs_checkpoint_ab", [PY, "scripts/build_deepnsm_hf_ollama_vs_checkpoint_ab_v1.py"], optional=True)
        )
    else:
        steps.append(
            {
                "label": "ollama_vs_checkpoint_ab",
                "cmd": ["skipped"],
                "exit_code": 0,
                "ok": True,
                "tail": "blocked_gated_llama_base",
            }
        )
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
                "pytest_deepnsm_checkpoint_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_deepnsm_hf_checkpoint_inference_v1.py",
                    "tests/test_deepnsm_hf_ollama_inference_v1.py",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    hf_chain = _read_json(HF_CHECKPOINT_CHAIN)
    ab_doc = _read_json(OLLAMA_VS_CKPT)
    phase14 = _read_json(PHASE14)
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}

    impl = hf_chain.get("implementation_status")
    pair_count = int(hf_chain.get("pair_count") or 0)
    hf_audit = hf_chain.get("hf_checkpoint_audit") or {}
    checkpoint_pilot_ok = (
        impl == "deepnsm_hf_checkpoint_v1"
        and bool(hf_chain.get("ok"))
        and pair_count >= 100
        and bool(hf_audit.get("gate_ok"))
    )
    phase14_ok = bool(phase14.get("all_ok"))
    ab_ready = bool(ab_doc.get("comparison_ready"))
    core_ok = all(
        s.get("ok")
        for s in steps
        if s.get("label") not in {"push_nl_research_pack", "checkpoint_prereqs"}
    )
    infrastructure_ok = core_ok and phase14_ok and bool(ev.get("all_enabled_planes_ok"))
    swap_blocked = not llama_gate_ok
    all_ok = infrastructure_ok and checkpoint_pilot_ok and ab_ready and not swap_blocked

    report = {
        "schema": "logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "infrastructure_ok": infrastructure_ok,
        "checkpoint_swap_status": "blocked_gated_llama_base" if swap_blocked else ("pilot_ok" if checkpoint_pilot_ok else "pending"),
        "llama_base_gate": (prereqs.get("checks") or {}).get("llama_base_gate"),
        "checkpoint_prereqs_ok": checkpoint_ready,
        "pilot_fixture": _rel(args.fixture),
        "phase14_carry_ok": phase14_ok,
        "deepnsm_hf_checkpoint": {
            "implementation_status": impl,
            "pair_count": pair_count,
            "checkpoint_model": (hf_chain.get("checkpoint_meta") or {}).get("checkpoint_model"),
            "base_model": (hf_chain.get("checkpoint_meta") or {}).get("base_model"),
            "hf_audit": hf_audit,
            "delta_hf_minus_gematria": hf_chain.get("delta_hf_checkpoint_minus_gematria"),
            "checkpoint_meta": hf_chain.get("checkpoint_meta"),
        },
        "ollama_vs_checkpoint_ab": {
            "comparison_ready": ab_ready,
            "delta_checkpoint_minus_ollama": ab_doc.get("delta_checkpoint_minus_ollama"),
            "report": "reports/deepnsm_hf_ollama_vs_checkpoint_ab_v1_latest.json",
        },
        "gate_eval_summary": {
            "research_ready_decision": ev.get("research_ready_decision"),
            "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
        },
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "pair_count": pair_count,
                "gate_spec_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
