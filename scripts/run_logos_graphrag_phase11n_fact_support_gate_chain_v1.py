#!/usr/bin/env python3
"""Phase 11-N: MERGED LIT_REVIEW full gate chain (fact_support fix) + bridge [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
MERGED_LIT = ROOT / "docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_MERGED_LIT_REVIEW_2026-06-21.md"
LIT_REVIEW = ROOT / "docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_LIT_REVIEW_2026-06-21.md"
GATE_CHAIN_OUT = ROOT / "reports/universal_root_lexicon_merged_lit_review_gate_chain_v1_latest.json"
BRIDGE_OUT = ROOT / "docs/final/artifacts/universal_root_research_impl_bridge_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11n_fact_support_gate_chain_v1_latest.json"
DEFAULT_QUERY = "universal root lexicon NSM layer A B C gating"


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
    ap.add_argument("--skip-merged-gate-chain", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_merged_gate_chain:
        gate_cmd = [
            PY,
            "scripts/run_mkm_merged_lit_review_gate_chain_v1.py",
            "--input",
            str(MERGED_LIT),
            "--query",
            DEFAULT_QUERY,
            "--min-total-ids",
            "3",
            "--min-total-claims",
            "3",
            "--out-json",
            str(GATE_CHAIN_OUT),
        ]
        if args.offline:
            gate_cmd.append("--offline")
        steps.append(_run("merged_lit_review_gate_chain", gate_cmd))

    steps.append(
        _run(
            "build_research_impl_bridge",
            [
                PY,
                "scripts/build_universal_root_research_impl_bridge_v1.py",
                "--gate-chain-json",
                str(GATE_CHAIN_OUT),
                "--strict",
            ],
        )
    )

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))

    if not args.skip_evidence_pack:
        steps.append(_run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_gate_spec_and_bridge",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_check_universal_root_gate_spec_v1.py",
                    "tests/test_build_universal_root_research_impl_bridge_v1.py",
                    "-q",
                    "--tb=short",
                ],
                optional=True,
            )
        )

    bridge_doc = _read_json(BRIDGE_OUT)
    gate_chain_doc = _read_json(GATE_CHAIN_OUT)
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    fact_doc = gate_chain_doc.get("fact_support") if isinstance(gate_chain_doc.get("fact_support"), dict) else {}
    fact_gate_ok = fact_doc.get("gate_ok")
    if fact_gate_ok is None:
        fact_gate_ok = fact_doc.get("ok")

    all_ok = (
        all(s.get("ok") for s in steps)
        and bool(bridge_doc.get("bridge_ok"))
        and bool(gate_chain_doc.get("ok"))
        and bool(fact_gate_ok)
    )

    report = {
        "schema": "logos_graphrag_phase11n_fact_support_gate_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "merged_lit_review_ssot": str(MERGED_LIT.relative_to(ROOT)).replace("\\", "/"),
        "lit_review_citation_source": str(LIT_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "bridge_ok": bridge_doc.get("bridge_ok"),
        "citation_lock_pass_rate": bridge_doc.get("citation_lock_pass_rate"),
        "fact_support_pass_rate": fact_doc.get("support_pass_rate"),
        "fact_support_gate_ok": fact_gate_ok,
        "gate_spec_phase": (bridge_doc.get("implementation_snapshot") or {}).get("gate_spec_phase"),
        "merged_gate_chain_ok": gate_chain_doc.get("ok"),
        "all_enabled_planes_ok": (gate_eval.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "bridge_artifact": str(BRIDGE_OUT.relative_to(ROOT)).replace("\\", "/"),
        "gate_chain_artifact": str(GATE_CHAIN_OUT.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11n_fact_support_gate_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "bridge_ok": bridge_doc.get("bridge_ok"),
                "fact_support_pass_rate": fact_doc.get("support_pass_rate"),
                "gate_spec_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
