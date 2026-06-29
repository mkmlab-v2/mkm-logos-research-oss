#!/usr/bin/env python3
"""Chain: Logos subgraph router gold eval + optional Magic Orb gold query eval [HYPO, B-track].

Reproducible:
  py scripts/run_logos_subgraph_gold_eval_chain_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SUBGRAPH_EVAL = ROOT / "scripts/run_logos_subgraph_gold_eval_v1.py"
GOLD_QUERY_EVAL = ROOT / "scripts/build_logos_gold_query_eval_report_v1.py"
SUBGRAPH_OUT = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"
GOLD_QUERY_OUT = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
CHAIN_OUT = ROOT / "reports/logos_subgraph_gold_eval_chain_v1_latest.json"


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
    ap.add_argument("--limit", type=int, default=0, help="Forward to subgraph eval (0=all)")
    ap.add_argument("--skip-gold-query-eval", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Subgraph eval exits 1 on gate fail")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    subgraph_cmd = [PY, str(SUBGRAPH_EVAL)]
    if args.limit > 0:
        subgraph_cmd.extend(["--limit", str(args.limit)])
    if args.strict:
        subgraph_cmd.append("--strict")
    steps.append(_run("subgraph_gold_eval", subgraph_cmd))

    gold_query_ran = False
    if not args.skip_gold_query_eval and GOLD_QUERY_EVAL.is_file():
        steps.append(_run("gold_query_eval", [PY, str(GOLD_QUERY_EVAL)], optional=True))
        gold_query_ran = steps[-1].get("ok", False)

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_subgraph_gold_eval",
                [PY, "-m", "pytest", "tests/test_run_logos_subgraph_gold_eval_v1.py", "-q", "--tb=short"],
            )
        )

    subgraph_summary: dict = {}
    if SUBGRAPH_OUT.is_file():
        subgraph_summary = json.loads(SUBGRAPH_OUT.read_text(encoding="utf-8-sig")).get("summary") or {}

    gold_query_summary: dict = {}
    if gold_query_ran and GOLD_QUERY_OUT.is_file():
        gold_query_summary = json.loads(GOLD_QUERY_OUT.read_text(encoding="utf-8-sig")).get("summary") or {}

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_subgraph_gold_eval_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "subgraph_eval_summary": subgraph_summary,
        "gold_query_eval_summary": gold_query_summary if gold_query_ran else None,
        "steps": steps,
        "reproduce": "py scripts/run_logos_subgraph_gold_eval_chain_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "hit_at_k_rates": subgraph_summary.get("hit_at_k_rates"),
                "gold_required_all_pass": subgraph_summary.get("gold_required_all_pass"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
