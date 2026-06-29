#!/usr/bin/env python3
"""TKM encounter_sequence chain: validate → summary → pytest [HYPO]."""

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
OUT = ROOT / "reports/tkm_encounter_sequence_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--append-fixture", action="store_true", help="Append example fixture to daily ledger")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(
        _run(
            "validate_sample",
            [PY, str(ROOT / "scripts/encounter_sequence_ledger_v1.py"), "validate-sample"],
        )
    )
    if steps[-1]["ok"]:
        steps.append(_run("build_summary", [PY, str(ROOT / "scripts/build_encounter_sequence_summary_v1.py")]))

    if steps and all(s["ok"] for s in steps) and args.append_fixture:
        fixture = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"
        raw = fixture.read_text(encoding="utf-8")
        steps.append(
            _run(
                "append_fixture",
                [PY, str(ROOT / "scripts/encounter_sequence_ledger_v1.py"), "append", "--json", raw],
            )
        )
        if steps[-1]["ok"]:
            steps.append(_run("build_summary_post_append", [PY, str(ROOT / "scripts/build_encounter_sequence_summary_v1.py")]))

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        t0 = time.perf_counter()
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_encounter_sequence_v1_schema.py",
                "tests/test_encounter_sequence_ledger_v1.py",
                "tests/test_build_encounter_sequence_summary_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "name": "pytest:encounter_sequence_suite",
                "exit_code": proc.returncode,
                "elapsed_sec": round(time.perf_counter() - t0, 2),
                "stdout_tail": (proc.stdout or "")[-300:],
                "ok": proc.returncode == 0,
            }
        )

    summary_path = ROOT / "reports/encounter_sequence_summary_v1_latest.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig")) if summary_path.is_file() else {}

    doc = {
        "schema": "tkm_encounter_sequence_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "sequence_count": summary.get("sequence_count"),
        "physician_agreement_rate": summary.get("physician_agreement_rate"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_tkm_encounter_sequence_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "sequence_count": doc.get("sequence_count")}))
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
