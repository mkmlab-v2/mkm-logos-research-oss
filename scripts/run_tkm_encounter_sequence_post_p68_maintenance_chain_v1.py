#!/usr/bin/env python3
"""TKM encounter_sequence post-P68 maintenance chain: drift obs + curated bulk review [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/tkm_encounter_sequence_post_p68_maintenance_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-http", action="store_true")
    ap.add_argument("--skip-p68-refresh", action="store_true")
    ap.add_argument("--with-gpu-interpret-train", action="store_true")
    ap.add_argument("--no-vault-mirror", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_p68_refresh:
        extra = ["--skip-http", "--skip-p67-refresh"]
        if args.with_gpu_interpret_train:
            extra.append("--with-gpu-interpret-train")
        if args.no_vault_mirror:
            extra.append("--no-vault-mirror")
        steps.append(_run("p68_freeze_verify", "run_tkm_encounter_sequence_p68_chain_v1.py", extra))

    if not steps or all(s["ok"] for s in steps):
        steps.extend(
            [
                _run("curated_review_milestone", "build_tkm_encounter_sequence_curated_review_milestone_v1.py"),
                _run(
                    "post_breakpoint_passive_drift_observation",
                    "build_tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1.py",
                ),
                _run("curated_bulk_human_review", "build_tkm_encounter_sequence_curated_bulk_human_review_v1.py"),
                _run("weekly_report", "build_encounter_sequence_weekly_report_v1.py"),
                _run("ops_closure", "build_tkm_encounter_sequence_ops_closure_v1.py"),
            ]
        )

    drift = ROOT / "reports/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
    bulk = ROOT / "reports/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"
    drift_doc = json.loads(drift.read_text(encoding="utf-8-sig")) if drift.is_file() else {}
    bulk_doc = json.loads(bulk.read_text(encoding="utf-8-sig")) if bulk.is_file() else {}

    if all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_encounter_sequence_post_p68_maintenance_v1.py",
                "tests/test_encounter_sequence_p68_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:post_p68_maintenance_suite",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "ok": proc.returncode == 0,
            }
        )

    core_steps_ok = all(s["ok"] for s in steps if not str(s.get("name", "")).startswith("pytest:"))
    maintenance_ok = (
        core_steps_ok
        and drift_doc.get("observation_ok") is True
        and bulk_doc.get("bulk_human_review_ok") is True
        and drift_doc.get("tier_inflation_forbidden") is True
    )
    doc = {
        "schema": "tkm_encounter_sequence_post_p68_maintenance_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "research_only": True,
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "post_p68_maintenance_ok": maintenance_ok,
        "passive_drift_observation_ok": drift_doc.get("observation_ok"),
        "curated_bulk_human_review_ok": bulk_doc.get("bulk_human_review_ok"),
        "ultra_grand_stack_breakpoint_freeze": drift_doc.get("ultra_grand_stack_breakpoint_freeze"),
        "tier_inflation_forbidden": True,
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_tkm_encounter_sequence_post_p68_maintenance_chain_v1.py --skip-http",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "maintenance": doc.get("post_p68_maintenance_ok")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
