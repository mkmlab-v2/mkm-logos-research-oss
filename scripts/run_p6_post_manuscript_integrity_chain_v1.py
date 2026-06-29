#!/usr/bin/env python3
"""P6 post-P5 closure: evidence sidecar refresh + operator board + digest + integration [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/p6_post_manuscript_integrity_chain_v1_latest.json"

STEPS = [
    ("evidence_sidecar", "build_cross_ref_entry_12_13_evidence_sidecar_v1.py"),
    ("promotion_gate", "build_dss_line_witness_promotion_gate_v1.py"),
    ("operator_board", "build_dss_line_witness_operator_board_v1.py"),
    ("waiting_queue", "append_entry_12_13_waiting_queue_v1.py"),
    ("dual_digest", "build_logos_commander_dual_theme_digest_v1.py"),
    ("integration_closure", "build_logos_track_b_integration_closure_v1.py"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run([PY, str(ROOT / "scripts" / script)], cwd=ROOT, capture_output=True, text=True)
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

    steps = [_run(n, s) for n, s in STEPS]
    if not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [PY, "-m", "pytest", "tests/test_p6_post_manuscript_integrity_v1.py", "-q"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest",
                "script": "tests/test_p6_post_manuscript_integrity_v1.py",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "stderr_tail": (proc.stderr or "")[-200:],
                "ok": proc.returncode == 0,
            }
        )

    closure_path = ROOT / "reports/logos_track_b_integration_closure_v1_latest.json"
    closure = {}
    if closure_path.is_file():
        closure = json.loads(closure_path.read_text(encoding="utf-8-sig"))

    all_ok = all(s["ok"] for s in steps) and closure.get("ok") is True
    doc = {
        "schema": "p6_post_manuscript_integrity_chain_v1",
        "generated_at_utc": _utc(),
        "delegation_scale": "M",
        "steps": steps,
        "integration_closure_ok": closure.get("ok"),
        "p5_manuscript_integrity_ok": (closure.get("gates") or {}).get("p5_manuscript_integrity_ok"),
        "ok": all_ok,
        "reproduce": "py scripts/run_p6_post_manuscript_integrity_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "integration_closure_ok": closure.get("ok")}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
