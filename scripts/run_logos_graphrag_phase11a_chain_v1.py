#!/usr/bin/env python3
"""Phase 11-A chain: NSM 500-pair audit + Logos subgraph gold re-eval [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11a_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-800:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-gold-eval", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: dict[str, dict] = {}

    steps["build_nsm_500_fixture"] = _run(
        [py, "scripts/build_nsm_41k_crosswalk_500_fixture_v1.py"]
    )
    steps["nsm_500_audit"] = _run(
        [
            py,
            "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
            "--fixture",
            "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
            "--expected-pairs",
            "500",
        ]
    )
    if not args.skip_gold_eval:
        steps["logos_subgraph_gold_eval"] = _run([py, "scripts/run_logos_subgraph_gold_eval_v1.py"])

    ok = all(s["exit_code"] == 0 for s in steps.values())
    nsm_report = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
    gold_report = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"
    nsm_summary = {}
    gold_summary = {}
    if nsm_report.is_file():
        nsm_doc = json.loads(nsm_report.read_text(encoding="utf-8"))
        base = nsm_doc.get("baseline") or {}
        nsm_summary = {
            "pair_count": base.get("pair_count"),
            "prime_hit_rate": base.get("prime_hit_rate"),
            "english_only_distortion_rate": base.get("english_only_distortion_rate"),
            "gate_ok": (nsm_doc.get("gates") or {}).get("gate_ok"),
        }
    if gold_report.is_file():
        gold_doc = json.loads(gold_report.read_text(encoding="utf-8"))
        summ = gold_doc.get("summary") or {}
        gold_summary = {
            "items_evaluated": summ.get("items_evaluated"),
            "hit_at_k_rates": summ.get("hit_at_k_rates"),
            "gold_required_all_pass": summ.get("gold_required_all_pass"),
        }

    out_doc = {
        "schema": "logos_graphrag_phase11a_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "steps": steps,
        "nsm_500_summary": nsm_summary,
        "gold_eval_summary": gold_summary,
        "reproduce": "py scripts/run_logos_graphrag_phase11a_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out), "nsm_500_summary": nsm_summary, "gold_summary": gold_summary}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
