#!/usr/bin/env python3
"""One-click FinOps wire domain v1 chain: push bundle → eval → closeout draft → pytest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports/finops_wire_domain_v1_chain_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "")[-600:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-export", action="store_true")
    ap.add_argument("--include-l3-grid", action="store_true", help="Run F-10 L3 restore grid after closeout")
    ap.add_argument(
        "--promote-official",
        action="store_true",
        help="After gates pass, promote L1 closeout (requires --commander-ack)",
    )
    ap.add_argument("--commander-ack", action="store_true", help="Commander approved L1 closeout promotion")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    push_cmd = [py, "scripts/build_finops_wire_push_bundle_v1.py", "--run-gloss", "--run-regression", "--run-wire-bench"]
    if not args.skip_export:
        push_cmd.extend(["--run-export"])
    steps.append({"step": "push_bundle", **_run(push_cmd)})
    steps.append({"step": "domain_eval", **_run([py, "scripts/run_finops_wire_domain_v1_eval_v1.py"])})
    steps.append({"step": "closeout_draft", **_run([py, "scripts/build_finops_wire_domain_v1_closeout_draft_v1.py"])})
    if args.include_l3_grid:
        steps.append({"step": "l3_restore_grid", **_run([py, "scripts/run_finops_wire_l3_restore_grid_v1.py"])})
    if args.promote_official:
        if not args.commander_ack:
            print(json.dumps({"ok": False, "error": "promote_official_requires_commander_ack"}))
            return 2
        promo_cmd = [
            py,
            "scripts/promote_finops_wire_domain_v1_closeout_official_v1.py",
            "--commander-ack",
        ]
        steps.append({"step": "promote_l1_official", **_run(promo_cmd)})
    steps.append(
        {
            "step": "pytest_finops",
            **_run(
                [
                    py,
                    "-m",
                    "pytest",
                    "tests/test_finops_wire_bench_holdout_v1.py",
                    "tests/test_finops_wire_domain_v1_eval_v1.py",
                    "tests/test_finops_wire_l3_restore_grid_v1.py",
                    "-q",
                ]
            ),
        }
    )
    steps.append(
        {
            "step": "weekly_smoke",
            **_run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1",
                ]
            ),
        }
    )

    ok = all(s.get("ok") for s in steps)
    log = {
        "ok": ok,
        "schema": "finops_wire_domain_v1_chain_v1",
        "generated_at_utc": _utc(),
        "branch_target": "b-track-finops-wire-v1",
        "steps": steps,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
