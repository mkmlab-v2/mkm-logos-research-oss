#!/usr/bin/env python3
"""B-track: verify Logos 4D topic spike CI demotion policy (contract smoke, not organic gate)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/logos_4d_topic_spike_ci_policy_v1.json"
CLOSURE = ROOT / "reports/logos_4d_ann_exploration_closure_v1_latest.json"
OUT = ROOT / "reports/logos_4d_topic_spike_ci_policy_check_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=POLICY)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument(
        "--skip-gold-check",
        action="store_true",
        help="Do not require reports/logos_gold_query_eval_v1_latest.json pass",
    )
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    policy = _read(args.policy_json)
    if policy.get("schema") != "logos_4d_topic_spike_ci_policy_v1":
        print(json.dumps({"ok": False, "error": "invalid policy schema"}))
        return 2

    organic = (policy.get("policy") or {}).get("organic_seed_intersection_top_k") or {}
    if organic.get("promotion_gate") is not False or organic.get("required_for_ci_pass") is not False:
        print(json.dumps({"ok": False, "error": "organic gate must stay demoted"}))
        return 2

    closure = _read(CLOSURE)
    gold_path = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
    gold = _read(gold_path)
    gold_pass = bool((gold.get("summary") or {}).get("gold_required_all_pass"))

    pytest_results: list[dict] = []
    if not args.skip_pytest:
        tests = (policy.get("policy") or {}).get("topic_spike_contract_smoke") or {}
        for rel in tests.get("tests") or []:
            cp = subprocess.run(
                [sys.executable, "-m", "pytest", str(ROOT / rel), "-q", "--tb=short"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            pytest_results.append(
                {
                    "test": rel,
                    "exit_code": cp.returncode,
                    "passed": cp.returncode == 0,
                }
            )

    pytest_ok = all(r["passed"] for r in pytest_results) if pytest_results else True
    if args.skip_pytest and args.skip_gold_check:
        ok = True
    elif args.skip_pytest:
        ok = gold_pass or args.skip_gold_check
    else:
        ok = pytest_ok and (gold_pass or args.skip_gold_check)

    doc = {
        "schema": "logos_4d_topic_spike_ci_policy_check_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "policy_json": str(args.policy_json.relative_to(ROOT)).replace("\\", "/"),
        "checks": {
            "policy_organic_demoted": True,
            "closure_present": closure.get("schema") == "logos_4d_ann_exploration_closure_v1",
            "gold_required_all_pass": gold_pass,
            "pytest_contract_smoke": pytest_results,
        },
        "ok": ok,
        "note": "Pass = gold router + contract pytest; organic seed∩top_k is NOT a gate.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out_json), "gold_pass": gold_pass}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
