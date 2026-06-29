#!/usr/bin/env python3
"""P9 Bible/Logos Track B final closure master chain [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/logos_bible_rail_p9_closure_chain_v1_latest.json"

STEPS = [
    ("evidence_sidecar", "build_cross_ref_entry_12_13_evidence_sidecar_v1.py"),
    ("verified_anchor_packet", "build_entry_13_ps5_2_verified_anchor_evidence_packet_v1.py"),
    ("verified_anchor_gate", "build_entry_13_ps5_2_verified_anchor_gate_v1.py"),
    ("psalms_cross_lane_audit", "build_psalms_entry_12_13_cross_lane_audit_v1.py"),
    ("p7_refresh", "run_entry_13_post_promotion_closure_chain_v1.py", ["--skip-pytest"]),
    ("completion_gate", "build_logos_bible_rail_completion_gate_v1.py"),
    ("completion_report", "build_logos_bible_rail_completion_commander_report_v1.py"),
    ("p9_waiting_queue", "append_bible_rail_p9_final_waiting_queue_v1.py"),
    ("ms_evidence_bundle", "bundle_logos_track_b_into_ms_evidence_pack_v1.py"),
]


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
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for item in STEPS:
        if len(item) == 3:
            name, script, extra = item
            steps.append(_run(name, script, extra))
        else:
            name, script = item  # type: ignore[misc]
            steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_logos_bible_rail_completion_v1.py",
            "tests/test_entry_13_ps5_2_verified_anchor_evidence_v1.py",
            "tests/test_cross_ref_dss_schema.py",
        ):
            t0 = time.perf_counter()
            proc = subprocess.run(
                [PY, "-m", "pytest", test_path, "-q"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            steps.append(
                {
                    "name": f"pytest:{test_path}",
                    "script": test_path,
                    "exit_code": proc.returncode,
                    "elapsed_sec": round(time.perf_counter() - t0, 2),
                    "stdout_tail": (proc.stdout or "")[-250:],
                    "stderr_tail": (proc.stderr or "")[-200:],
                    "ok": proc.returncode == 0,
                }
            )
            if proc.returncode != 0:
                break

    gate_path = ROOT / "docs/final/artifacts/logos_bible_rail_completion_gate_v1_latest.json"
    gate = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "logos_bible_rail_p9_closure_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "bible_rail_status": gate.get("bible_rail_status"),
        "completion_gate_ok": gate.get("gate_ok"),
        "reproduce": "py scripts/run_logos_bible_rail_p9_closure_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "bible_rail_status": doc.get("bible_rail_status"),
                "steps": len(steps),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
