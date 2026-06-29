#!/usr/bin/env python3
"""Phase 10-A: gold miss forensics → registry refresh → gold eval → evidence pack [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CHAIN_OUT = ROOT / "reports/logos_graphrag_phase10_miss_tune_chain_v1_latest.json"


def _utc_now() -> str:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-registry", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_registry:
        steps.append(_run("concept_bridge_registry", [PY, "scripts/build_logos_concept_bridge_registry_v1.py"]))

    steps.append(_run("subgraph_gold_eval", [PY, "scripts/run_logos_subgraph_gold_eval_v1.py"]))
    steps.append(
        _run(
            "gold_miss_forensics",
            [PY, "scripts/run_logos_subgraph_gold_miss_forensics_v1.py", "--skip-gold-eval"],
        )
    )
    steps.append(_run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_router_gold",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_run_logos_subgraph_graphrag_router_v1.py",
                    "tests/test_run_logos_subgraph_gold_eval_v1.py",
                    "-q",
                    "--tb=short",
                ],
            )
        )

    forensics = ROOT / "reports/logos_subgraph_gold_miss_forensics_v1_latest.json"
    gold_eval = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"
    forensics_doc = json.loads(forensics.read_text(encoding="utf-8-sig")) if forensics.is_file() else {}
    gold_doc = json.loads(gold_eval.read_text(encoding="utf-8-sig")) if gold_eval.is_file() else {}
    gold_summary = gold_doc.get("summary") if isinstance(gold_doc.get("summary"), dict) else {}

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_graphrag_phase10_miss_tune_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "router_version": gold_doc.get("router_version"),
        "hit_at_k_rates": gold_summary.get("hit_at_k_rates"),
        "gold_required_all_pass": gold_summary.get("gold_required_all_pass"),
        "forensics_miss_rows": len(forensics_doc.get("rows") or []),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase10_miss_tune_chain_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "hit_at_k_rates": gold_summary.get("hit_at_k_rates"),
                "gold_required_all_pass": gold_summary.get("gold_required_all_pass"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
