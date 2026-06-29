#!/usr/bin/env python3
"""P4 chain: verification scan + evidence sidecar + promotion gate + operator board [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/dss_line_witness_verification_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str, *extra: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script), *extra]
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
    ap.add_argument("--apply-promotion", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps = [
        _run("verification_scan", "build_dss_line_witness_verification_scan_v1.py"),
        _run("evidence_sidecar", "build_cross_ref_entry_12_13_evidence_sidecar_v1.py"),
        _run("promotion_gate", "build_dss_line_witness_promotion_gate_v1.py"),
        _run("operator_board", "build_dss_line_witness_operator_board_v1.py"),
        _run("waiting_queue_append", "append_entry_12_13_waiting_queue_v1.py"),
    ]
    promo_args = ["--apply"] if args.apply_promotion else []
    steps.append(_run("apply_promotion", "apply_dss_line_witness_promotion_v1.py", *promo_args))
    if args.apply_promotion:
        steps.extend(
            [
                _run("4q_registry_refresh", "build_shadow_4q_ps5_witness_registry_v1.py"),
                _run("witness_registry_refresh", "build_shadow_line_witness_registry_v1.py"),
                _run("xref_refresh", "build_shadow_canon_gematria_xref_map_v1.py"),
                _run("cross_lane_audit", "build_shadow_cross_lane_gematria_audit_v1.py"),
                _run("p6_refresh", "run_p6_post_manuscript_integrity_chain_v1.py", "--skip-pytest"),
            ]
        )
    if not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_dss_line_witness_verification_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest",
                "script": "tests/test_dss_line_witness_verification_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "stderr_tail": (proc.stderr or "")[-200:],
                "ok": proc.returncode == 0,
            }
        )

    gate_path = ROOT / "docs/final/artifacts/dss_line_witness_promotion_gate_v1_latest.json"
    gate = {}
    if gate_path.is_file():
        gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    all_ok = all(s["ok"] for s in steps) and gate.get("gate_ok") is True
    doc = {
        "schema": "dss_line_witness_verification_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "delegation_scale": "M",
        "steps": steps,
        "gate_ok": gate.get("gate_ok"),
        "promotion_ok": gate.get("promotion_ok"),
        "promotion_pending_external": gate.get("promotion_pending_external"),
        "ok": all_ok,
        "reproduce": "py scripts/run_dss_line_witness_verification_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "gate_ok": gate.get("gate_ok"),
                "promotion_ok": gate.get("promotion_ok"),
                "promotion_pending_external": gate.get("promotion_pending_external"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
