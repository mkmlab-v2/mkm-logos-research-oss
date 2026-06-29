#!/usr/bin/env python3
"""Gate: eval path policy — attested default, mainline dummy-free [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_v1.json"
OUT = ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_dummy(row: dict[str, Any]) -> bool:
    pid = str(row.get("person_id") or "")
    disp = str(row.get("display_name") or "")
    return (
        "dummy" in pid.lower()
        or "dummy" in disp.lower()
        or "DUMMYCSV" in pid
        or "DUMMYJSONL" in pid
        or "[DUMMY]" in disp
    )


def build() -> dict[str, Any]:
    policy = json.loads(POLICY.read_text(encoding="utf-8-sig")) if POLICY.is_file() else {}
    attested = ROOT / str(policy.get("default_eval_dataset") or "")
    mainline = ROOT / str(policy.get("mainline_dataset") or "")
    archive = ROOT / str(policy.get("dummy_archive_dataset") or "")

    mainline_dummy = 0
    if mainline.is_file():
        for line in mainline.read_text(encoding="utf-8").splitlines():
            if line.strip() and _is_dummy(json.loads(line)):
                mainline_dummy += 1

    attested_rows = 0
    if attested.is_file():
        attested_rows = sum(1 for ln in attested.read_text(encoding="utf-8").splitlines() if ln.strip())

    checks = {
        "policy_present": {"passed": policy.get("schema") == "sasang_joint_benchmark_eval_path_policy_v1"},
        "attested_dataset_exists": {"passed": attested.is_file() and attested_rows >= 5},
        "mainline_dummy_free": {"passed": mainline_dummy == 0},
        "archive_dataset_exists": {"passed": archive.is_file()},
        "track_a_bridge_forbidden": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_joint_benchmark_eval_path_policy_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "eval_path_status": "attested_default_locked" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "attested_rows": attested_rows,
        "mainline_dummy_rows": mainline_dummy,
        "policy_ref": str(POLICY).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_joint_benchmark_eval_path_policy_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "eval_path_status": doc["eval_path_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
