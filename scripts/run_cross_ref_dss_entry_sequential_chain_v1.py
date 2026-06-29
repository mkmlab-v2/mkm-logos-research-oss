#!/usr/bin/env python3
"""P10: sequential DSS entry rail chain ENTRY_01–16 + waiting-queue hunts [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/cross_ref_dss_entry_sequential_chain_v1_latest.json"

STEPS = [
    ("slot_mapping", "build_logos_dss_crossref_slot_mapping_v1.py"),
    ("wq_seed_entry07", "seed_entry07_source_hunt_from_qd_v1.py"),
    ("wq_seed_entry08", "seed_entry08_source_hunt_from_qd_v1.py"),
    ("wq_report_entry16", "report_entry16_source_hunt.py"),
    ("rail_packets", "build_cross_ref_dss_entry_rail_packet_v1.py", ["--all"]),
    ("artifact_paths", "apply_cross_ref_dss_entry_rail_artifact_paths_v1.py", ["--apply"]),
    ("strict_audit", "build_logos_dss_crossref_strict_gate_audit_v1.py"),
    ("sequential_gate", "build_cross_ref_dss_entry_sequential_gate_v1.py"),
    ("p9_gate_refresh", "build_logos_bible_rail_completion_gate_v1.py"),
    ("dual_digest", "build_logos_commander_dual_theme_digest_v1.py"),
    ("ms_bundle", "bundle_logos_track_b_into_ms_evidence_pack_v1.py"),
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
            "tests/test_cross_ref_dss_entry_sequential_rail_v1.py",
            "tests/test_cross_ref_dss_schema.py",
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

    gate_path = ROOT / "docs/final/artifacts/cross_ref_dss_entry_sequential_gate_v1_latest.json"
    gate = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "cross_ref_dss_entry_sequential_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "sequential_rail_status": gate.get("sequential_rail_status"),
        "gate_ok": gate.get("gate_ok"),
        "reproduce": "py scripts/run_cross_ref_dss_entry_sequential_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["all_ok"], "sequential_rail_status": doc.get("sequential_rail_status")},
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
