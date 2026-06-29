#!/usr/bin/env python3
"""Refresh 4D demotion monitoring snapshot (no remediation attempts)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_4d_monitoring_snapshot_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--skip-policy-check", action="store_true")
    args = ap.parse_args()

    policy_exit = 0
    policy_stdout = ""
    if not args.skip_policy_check:
        cp = subprocess.run(
            [sys.executable, str(ROOT / "scripts/check_logos_4d_topic_spike_ci_policy_v1.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        policy_exit = cp.returncode
        policy_stdout = (cp.stdout or "").strip()[-800:]

    closure = _read(ROOT / "reports/logos_4d_ann_exploration_closure_v1_latest.json")
    collapse = _read(ROOT / "reports/logos_4d_total_value_collapse_v1_latest.json")
    compare = _read(ROOT / "reports/logos_4d_bridge_v2_poc_compare_v1_latest.json")
    policy_check = _read(ROOT / "reports/logos_4d_topic_spike_ci_policy_check_v1_latest.json")

    doc = {
        "schema": "logos_4d_monitoring_snapshot_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "role": "demoted_monitoring_only",
        "policy_check_exit": policy_exit,
        "policy_check_ok": policy_exit == 0,
        "organic_4d_topic_spike": (closure.get("verdict") or {}).get("organic_4d_topic_spike"),
        "collapse_row_fraction": (collapse.get("summary") or {}).get("collapse_row_fraction")
        or (closure.get("root_cause_ranked") or [{}])[0].get("collapse_row_fraction"),
        "bridge_v2_dup_fraction": (compare.get("summary") or {}).get("duplicate_verse_fraction_v2"),
        "bridge_v2_organic_spike": (compare.get("summary") or {}).get("organic_topic_spike_v2"),
        "ci_policy": policy_check.get("policy_path") or "docs/final/artifacts/logos_4d_topic_spike_ci_policy_v1.json",
        "operator_note_ko": "4D는 감시만 — 승격·재compute 루프 중단 권고.",
        "pointers": {
            "closure": "reports/logos_4d_ann_exploration_closure_v1_latest.json",
            "policy_check": "reports/logos_4d_topic_spike_ci_policy_check_v1_latest.json",
        },
    }
    if policy_stdout:
        doc["policy_check_tail"] = policy_stdout

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = policy_exit == 0
    print(json.dumps({"ok": ok, "policy_check": ok, "out": str(args.out_json)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
