#!/usr/bin/env python3
"""Curated learning ack router — human vs dummy autofill [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/encounter_sequence_curated_learning_ack_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(*, mode: str) -> dict[str, Any]:
    if mode not in {"human", "dummy"}:
        return {"ok": False, "reason": "invalid_mode", "mode": mode}
    extra = ["--human-gate-ack"] if mode == "human" else ["--dummy-auto-fill"]
    proc = subprocess.run(
        [PY, str(ROOT / "scripts/apply_encounter_sequence_curated_learning_v1.py"), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    apply_doc: dict[str, Any] = {}
    try:
        apply_doc = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        apply_doc = {"raw_stdout": (proc.stdout or "")[-300:]}

    ack_doc = json.loads(ACK.read_text(encoding="utf-8-sig")) if ACK.is_file() else {}
    mutual_exclusive_ok = True
    if mode == "human":
        mutual_exclusive_ok = ack_doc.get("dummy_autofill") is not True
    else:
        mutual_exclusive_ok = ack_doc.get("dummy_autofill") is True

    return {
        "schema": "encounter_sequence_curated_learning_ack_v1",
        "generated_at_utc": _utc(),
        "mode": mode,
        "ok": proc.returncode == 0 and apply_doc.get("applied") is True and mutual_exclusive_ok,
        "apply": apply_doc,
        "ack_ref": str(ACK).replace("\\", "/"),
        "note_ko": "human=원장·운영자 ack; dummy=B-track autofill only",
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["human", "dummy"], required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run(mode=args.mode)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "mode": args.mode}))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
