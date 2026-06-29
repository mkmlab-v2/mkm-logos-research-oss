#!/usr/bin/env python3
"""One-click TKM encounter_sequence stack with dummy autofill [HYPO]."""

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
OUT = ROOT / "reports/tkm_encounter_sequence_stack_autofill_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_chain(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-weekly-register", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    extra = ["--skip-http"]
    if args.skip_pytest:
        extra.append("--skip-pytest")

    steps = [_run_chain("post_p68_maintenance", "run_tkm_encounter_sequence_post_p68_maintenance_chain_v1.py", extra)]

    chain = ROOT / "reports/tkm_encounter_sequence_post_p68_maintenance_chain_v1_latest.json"
    chain_doc = json.loads(chain.read_text(encoding="utf-8-sig")) if chain.is_file() else {}
    autofill = ROOT / "reports/tkm_encounter_sequence_dummy_autofill_v1_latest.json"
    fill = json.loads(autofill.read_text(encoding="utf-8-sig")) if autofill.is_file() else {}

    doc = {
        "schema": "tkm_encounter_sequence_stack_autofill_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "dummy_autofill": True,
        "send_gate": "HOLD",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "post_p68_maintenance_ok": chain_doc.get("post_p68_maintenance_ok"),
        "passive_drift_observation_ok": chain_doc.get("passive_drift_observation_ok"),
        "curated_bulk_human_review_ok": chain_doc.get("curated_bulk_human_review_ok"),
        "clinic_capture_count": fill.get("clinic_capture_count"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_stack_autofill_v1.py",
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "clinic_capture_count": doc.get("clinic_capture_count")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
