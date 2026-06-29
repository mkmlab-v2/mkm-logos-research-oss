#!/usr/bin/env python3
"""P12 Bible/Logos Track B closure: phase3 sync + waiting-queue consolidated gate [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/logos_bible_rail_p12_closure_chain_v1_latest.json"

STEPS = [
    ("sequential_rail", "run_cross_ref_dss_entry_sequential_chain_v1.py"),
    ("phase3_snapshot_sync", "sync_btrack_phase3_snapshot_json_fence.py", ["--apply"]),
    ("entry16_promotion_gate", "evaluate_entry16_promotion_gate.py"),
    ("waiting_queue_gate", "build_cross_ref_waiting_queue_consolidated_gate_v1.py"),
    ("p11_waiting_queue_log", "append_bible_rail_p11_sequential_waiting_queue_v1.py"),
    ("completion_gate_refresh", "build_logos_bible_rail_completion_gate_v1.py"),
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
            "tests/test_btrack_phase3_snapshot_sync.py",
            "tests/test_cross_ref_dss_entry_sequential_rail_v1.py",
            "tests/test_logos_bible_rail_p12_closure_v1.py",
        ):
            t0 = time.perf_counter()
            proc = subprocess.run([PY, "-m", "pytest", test_path, "-q"], cwd=ROOT, capture_output=True, text=True)
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

    wq_path = ROOT / "docs/final/artifacts/cross_ref_waiting_queue_consolidated_gate_v1_latest.json"
    wq = {}
    if wq_path.is_file():
        wq = json.loads(wq_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "logos_bible_rail_p12_closure_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "waiting_queue_status": wq.get("waiting_queue_status"),
        "waiting_queue_gate_ok": wq.get("gate_ok"),
        "reproduce": "py scripts/run_logos_bible_rail_p12_closure_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "waiting_queue_status": doc.get("waiting_queue_status"),
                "steps": len(steps),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
