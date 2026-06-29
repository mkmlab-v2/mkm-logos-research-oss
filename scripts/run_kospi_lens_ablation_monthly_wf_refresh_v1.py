#!/usr/bin/env python3
"""Charter R4 — KOSPI lens ablation monthly walk-forward refresh [HYPO][research_only].

Runs walk-forward ablation chain + optional pytest smoke; writes audit JSON.
Does NOT promote Track A / ensemble / live trading.
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
DEFAULT_OUT = ROOT / "reports/kospi_lens_ablation_monthly_wf_refresh_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_lens_ablation_monthly_wf_refresh_v1_latest.json"
WF_JSON = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
SNAPSHOT_JSON = ROOT / "reports/kospi_lens_ablation_backtest_latest.json"
SUMMARY_JSON = ROOT / "reports/kospi_lens_ablation_snapshot_vs_walkforward_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _run(cmd: list[str], *, label: str) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "step": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def _slim_wf_pointer(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    best = doc.get("best_arm") or {}
    metrics = best.get("metrics") or {}
    return {
        "path": _rel(path),
        "window": doc.get("window"),
        "best_arm_id": best.get("arm_id"),
        "soft_hit_rate": metrics.get("soft_hit_rate"),
        "four_ai_overlay_uplift_pp": doc.get("four_ai_overlay_uplift_pp_vs_lens3_runtime"),
        "n_arms": len(doc.get("arms") or []),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="1996-12-11")
    ap.add_argument("--date-to", default="2026-06-05")
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--skip-jsonl-build", action="store_true", help="Faster audit; monthly prod omits this.")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; no subprocess side effects.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    plan = {
        "fetch_kospi": not args.skip_fetch,
        "jsonl_build": not args.skip_jsonl_build,
        "walkforward_ablation": True,
        "snapshot_vs_walkforward_summary": True,
        "pytest_smoke": not args.skip_pytest,
    }

    steps: list[dict[str, Any]] = []
    exit_code = 0

    if args.dry_run:
        doc = {
            "schema": "kospi_lens_ablation_monthly_wf_refresh_v1",
            "generated_at_utc": _utc_now(),
            "hypothesis_tag": "[HYPO]",
            "research_only": True,
            "charter_ref": "LENS_UTILIZATION_CHARTER_V1 R4",
            "dry_run": True,
            "plan": plan,
            "steps": [],
            "pointers": {
                "walkforward": _rel(WF_JSON),
                "snapshot": _rel(SNAPSHOT_JSON),
                "snapshot_vs_walkforward": _rel(SUMMARY_JSON),
            },
            "verdict": "dry_run_ok",
            "auto_promote": False,
        }
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ART_OUT.parent.mkdir(parents=True, exist_ok=True)
        ART_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "out": str(args.out_json)}))
        return 0

    py = sys.executable
    if not args.skip_fetch:
        step = _run(
            [py, "scripts/fetch_kospi_yfinance_csv.py", "--start", args.date_from],
            label="fetch_kospi_yfinance_csv",
        )
        steps.append(step)
        if step["exit_code"] != 0:
            exit_code = step["exit_code"]

    if exit_code == 0:
        ps1 = ROOT / "scripts/Invoke-KospiLensAblationWalkforward_v1.ps1"
        ps_args = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1),
            "-DateFrom",
            args.date_from,
            "-DateTo",
            args.date_to,
            "-BuildSnapshotVsWalkforwardSummary",
        ]
        if args.skip_jsonl_build:
            ps_args.append("-SkipJsonlBuild")
        step = _run(ps_args, label="invoke_kospi_lens_ablation_walkforward")
        steps.append(step)
        if step["exit_code"] != 0:
            exit_code = step["exit_code"]

    if exit_code == 0 and not args.skip_pytest:
        step = _run(
            [py, "-m", "pytest", "tests/test_run_kospi_lens_ablation_backtest_v1.py", "-q"],
            label="pytest_kospi_lens_ablation_smoke",
        )
        steps.append(step)
        if step["exit_code"] != 0:
            exit_code = step["exit_code"]

    wf_ptr = _slim_wf_pointer(WF_JSON)
    snap_ptr = _slim_wf_pointer(SNAPSHOT_JSON)
    summary_ptr = None
    if SUMMARY_JSON.is_file():
        summary_ptr = {"path": _rel(SUMMARY_JSON)}

    doc = {
        "schema": "kospi_lens_ablation_monthly_wf_refresh_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "charter_ref": "LENS_UTILIZATION_CHARTER_V1 R4",
        "dry_run": False,
        "plan": plan,
        "steps": [{k: v for k, v in s.items() if k != "cmd"} for s in steps],
        "pointers": {
            "walkforward": wf_ptr,
            "snapshot": snap_ptr,
            "snapshot_vs_walkforward": summary_ptr,
        },
        "verdict": "ok" if exit_code == 0 else "fail",
        "auto_promote": False,
        "operator_lines": [
            "- [MKM-KOSPI-ABLATION-WF] monthly refresh; Track A / ensemble untouched.",
            f"- [MKM-KOSPI-ABLATION-WF] walkforward best={((wf_ptr or {}).get('best_arm_id'))} "
            f"soft={((wf_ptr or {}).get('soft_hit_rate'))}",
            f"- [MKM-KOSPI-ABLATION-WF] exit={exit_code}",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": exit_code == 0,
                "exit_code": exit_code,
                "out": str(args.out_json),
                "verdict": doc["verdict"],
            },
            ensure_ascii=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
