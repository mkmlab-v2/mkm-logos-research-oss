#!/usr/bin/env python3
"""Path A spine commercial defense chain — microgrid · B2B billable eval · fact sheet.

M-scale delegation AUTO (local Fact-Lock). send_gate HOLD · apply_active forbidden.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/path_a_spine_commercial_defense_chain_v1_latest.json"
B2B_BENCH = ROOT / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_B2B_SPINE_BENCH_INPUT_V1.json"
B2B_EVAL = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_b2b_spine_binary_billable_eval_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "parsed": parsed,
        "tail": tail[-2:] if tail else [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-microgrid", action="store_true")
    ap.add_argument("--skip-masked-cohort", action="store_true")
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    if not args.skip_microgrid:
        steps["microgrid"] = _run([sys.executable, "scripts/run_ng40_path_a_keep_ratio_microgrid_v1.py"])
        ok = ok and steps["microgrid"]["ok"]

    steps["b2b_spine_eval"] = _run(
        [
            sys.executable,
            "scripts/run_nextgen_spine_binary_billable_eval_v1.py",
            "--bench-input",
            str(B2B_BENCH.relative_to(ROOT)).replace("\\", "/"),
            "--out-json",
            str(B2B_EVAL.relative_to(ROOT)).replace("\\", "/"),
            "--arm-id",
            "ng40_b2b_spine_binary_billable_v1",
            "--bench-label",
            "b2b_longform",
        ]
    )
    ok = ok and steps["b2b_spine_eval"]["ok"]

    if not args.skip_masked_cohort:
        steps["masked_cohort"] = _run(
            [
                sys.executable,
                "scripts/run_ng40_path_a_customer_masked_cohort_chain_v1.py",
                "--rows",
                "25",
            ]
        )
        ok = ok and steps["masked_cohort"]["ok"]

    steps["export_pack"] = _run([sys.executable, "scripts/build_ng40_b2b_product_export_pack_v1.py"])
    ok = ok and steps["export_pack"]["ok"]

    steps["fact_sheet"] = _run(
        [sys.executable, "scripts/build_path_a_spine_commercial_defense_fact_sheet_v1.py"]
    )
    ok = ok and steps["fact_sheet"]["ok"]

    fact = {}
    fact_path = ROOT / "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json"
    if fact_path.is_file():
        fact = json.loads(fact_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "path_a_spine_commercial_defense_chain_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_active_forbidden": True,
        "chain_ok": ok,
        "steps": steps,
        "product_kpi": {
            "global_token_saving_percent": (fact.get("product_lane") or {}).get(
                "global_token_saving_percent"
            ),
            "byte_exact_subset_parity": (fact.get("product_lane") or {}).get(
                "byte_exact_subset_parity"
            ),
            "product_ready": (fact.get("product_lane") or {}).get("product_ready"),
        },
        "fact_sheet_pointer": "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json",
        "paste_pointer": "reports/human_paste/path_a_spine_commercial_defense_fact_sheet_v1_latest.txt",
        "reproducible_command": "py scripts/run_path_a_spine_commercial_defense_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "chain_ok": ok,
                "out": str(OUT),
                "saving_percent": doc["product_kpi"]["global_token_saving_percent"],
                "byte_exact": doc["product_kpi"]["byte_exact_subset_parity"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
