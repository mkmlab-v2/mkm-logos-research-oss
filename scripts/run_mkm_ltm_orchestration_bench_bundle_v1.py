#!/usr/bin/env python3
"""Run MKM LTM orchestration bench bundle — token + cap ablation + prior-art log ([HYPO]).

  py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py
  py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py --run-bridge-chain
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(rel: str, *extra: str) -> tuple[int, str]:
    cmd = [PY, str(ROOT / rel), *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-1200:]
    return proc.returncode, tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-bridge-chain", action="store_true")
    ap.add_argument("--skip-prior-art-seed", action="store_true")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports/mkm_ltm_orchestration_bench_bundle_v1_latest.json",
    )
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    errors: list[str] = []

    if not args.skip_prior_art_seed:
        code, tail = _run("scripts/append_mkm_prior_art_search_log_v1.py", "--seed-template")
        steps["prior_art_seed"] = {"ok": code == 0, "exit_code": code, "tail": tail}
        if code != 0:
            errors.append(f"prior_art_seed exit {code}")

    code, tail = _run("scripts/append_mkm_prior_art_search_log_v1.py", "--validate-only")
    steps["prior_art_validate"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"prior_art_validate exit {code}")

    orch_args: list[str] = []
    if args.run_bridge_chain:
        orch_args.append("--run-bridge-chain")
    code, tail = _run("scripts/build_mkm_ltm_orchestration_bench_v1.py", *orch_args)
    steps["orchestration_bench"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"orchestration_bench exit {code}")

    code, tail = _run("scripts/build_mkm_ltm_insight_cap_ablation_bench_v1.py")
    steps["cap_ablation_bench"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"cap_ablation_bench exit {code}")

    code, tail = _run("scripts/build_logos_gold_query_eval_report_v1.py", "--strict")
    steps["gold_query_eval"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"gold_query_eval exit {code}")

    code, tail = _run("scripts/build_mkm_ltm_insight_cap_gold_regression_v1.py")
    steps["cap_gold_regression"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"cap_gold_regression exit {code}")

    doc: dict[str, Any] = {
        "schema": "mkm_ltm_orchestration_bench_bundle_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "steps": steps,
        "artifacts": {
            "orchestration_bench": "reports/mkm_ltm_orchestration_bench_v1_latest.json",
            "cap_ablation_bench": "reports/mkm_ltm_insight_cap_ablation_bench_v1_latest.json",
            "cap_gold_regression": "reports/mkm_ltm_insight_cap_gold_regression_v1_latest.json",
            "gold_query_eval": "reports/logos_gold_query_eval_v1_latest.json",
            "prior_art_log": "docs/research/nextgen_ltm_knowledge_os/PRIOR_ART_SEARCH_LOG.jsonl",
        },
        "ok": not errors,
        "errors": errors,
        "reproduce": "py scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.out.relative_to(ROOT)).replace("\\", "/")}))

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
