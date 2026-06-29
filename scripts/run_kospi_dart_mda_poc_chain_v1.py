#!/usr/bin/env python3
"""HD tier_0 chain — KOSPI DART MD&A PoC: ingest → Gate A → pytest.

B-track only · send_gate HOLD · no Track A / live trading.

Reproduce:
  py scripts/run_kospi_dart_mda_poc_chain_v1.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/kospi_dart_mda_poc_hd_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(label: str, cmd: list[str]) -> int:
    print(f"[kospi-dart-poc] {label}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"[kospi-dart-poc] FAIL {label} exit={proc.returncode}", file=sys.stderr)
    return proc.returncode


def main() -> int:
    steps: list[tuple[str, list[str]]] = [
        ("bootstrap_zip_fixture", [PY, "scripts/bootstrap_dart_mda_fixture_zip_v1.py"]),
        (
            "ingest_fixture",
            [PY, "scripts/ingest_dart_mda_section_v1.py", "--mode", "fixture"],
        ),
        (
            "ingest_dart_zip_fixture",
            [
                PY,
                "scripts/ingest_dart_mda_section_v1.py",
                "--mode",
                "dart_zip",
                "--zip-file",
                "tests/fixtures/dart_mda_document_v1.zip",
                "--out",
                "reports/kospi_dart_mda_corpus_zip_fixture_v1_latest.json",
            ],
        ),
        ("gate_a", [PY, "scripts/check_kospi_dart_mda_poc_gate_v1.py"]),
        ("gate_b_timing_sheet", [PY, "scripts/build_kospi_dart_mda_poc_human_timing_v1.py"]),
        ("live_smoke_optional", [PY, "scripts/run_kospi_dart_mda_poc_live_smoke_v1.py"]),
        ("pytest", [PY, "-m", "pytest", "tests/test_kospi_dart_mda_poc_gate_v1.py", "-q"]),
    ]

    results: list[dict[str, object]] = []
    for label, cmd in steps:
        code = _run(label, cmd)
        results.append({"step": label, "exit_code": code, "ok": code == 0})
        if code != 0:
            break

    ok = bool(results) and all(r["ok"] for r in results)
    doc = {
        "schema": "kospi_dart_mda_poc_hd_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tier": "B",
        "wires_to_scoring_core": False,
        "ok": ok,
        "steps": results,
        "gate_artifact": "docs/final/artifacts/kospi_dart_mda_poc_latest.json",
        "reproduce": "py scripts/run_kospi_dart_mda_poc_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "artifact": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
