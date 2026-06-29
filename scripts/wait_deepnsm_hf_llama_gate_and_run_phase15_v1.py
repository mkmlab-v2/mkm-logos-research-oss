#!/usr/bin/env python3
"""Poll Llama base HF gate; run Phase 15 when access opens [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/deepnsm_hf_llama_gate_wait_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _llama_gate_ok() -> tuple[bool, dict]:
    proc = subprocess.run(
        [PY, "scripts/check_deepnsm_hf_checkpoint_prereqs_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc_path = ROOT / "reports/deepnsm_hf_checkpoint_prereqs_v1_latest.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8-sig")) if doc_path.is_file() else {}
    gate = (doc.get("checks") or {}).get("llama_base_gate") or {}
    return proc.returncode == 0 and bool(gate.get("ok")), {
        "prereqs_exit_code": proc.returncode,
        "llama_base_gate": gate,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--interval-sec", type=int, default=15)
    ap.add_argument("--max-wait-sec", type=int, default=600)
    ap.add_argument("--run-phase15-on-open", action="store_true", default=True)
    ap.add_argument("--skip-nl-push", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    started = time.time()
    attempts = 0
    last: dict = {}
    while True:
        attempts += 1
        ok, last = _llama_gate_ok()
        if ok:
            break
        if time.time() - started >= args.max_wait_sec:
            doc = {
                "schema": "deepnsm_hf_llama_gate_wait_v1",
                "generated_at_utc": _utc(),
                "status": "timeout",
                "attempts": attempts,
                "last_check": last,
                "accept_url": "https://huggingface.co/meta-llama/Llama-3.2-1B",
                "note": "Log in as moksorinw and click Agree and access repository on model page",
            }
            args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ok": False, "status": "timeout", "out": str(args.out)}, ensure_ascii=False))
            return 1
        time.sleep(max(args.interval_sec, 5))

    phase15_rc = None
    if args.run_phase15_on_open:
        cmd = [PY, "scripts/run_logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1.py"]
        if args.skip_nl_push:
            cmd.append("--skip-nl-push")
        proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
        phase15_rc = proc.returncode

    doc = {
        "schema": "deepnsm_hf_llama_gate_wait_v1",
        "generated_at_utc": _utc(),
        "status": "gate_open",
        "attempts": attempts,
        "last_check": last,
        "phase15_exit_code": phase15_rc,
        "accept_url": "https://huggingface.co/meta-llama/Llama-3.2-1B",
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": phase15_rc == 0, "status": "gate_open", "phase15_rc": phase15_rc}, ensure_ascii=False))
    return 0 if phase15_rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
