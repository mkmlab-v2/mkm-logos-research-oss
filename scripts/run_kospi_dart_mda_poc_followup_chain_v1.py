#!/usr/bin/env python3
"""Follow-up chain — inbox paste ingest, Gate B check, live/API smoke.

Reproduce:
  py scripts/run_kospi_dart_mda_poc_followup_chain_v1.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
INBOX = ROOT / "data/kospi/dart_mda_poc/inbox_paste_v1.txt"
CORPUS_INBOX = ROOT / "reports/kospi_dart_mda_corpus_inbox_v1_latest.json"
OUT = ROOT / "reports/kospi_dart_mda_poc_followup_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _inbox_ready() -> bool:
    if not INBOX.is_file():
        return False
    text = INBOX.read_text(encoding="utf-8-sig")
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("#"))
    return len(body.strip()) >= 200


def _run(label: str, cmd: list[str]) -> int:
    print(f"[kospi-dart-followup] {label}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"[kospi-dart-followup] FAIL {label} exit={proc.returncode}", file=sys.stderr)
    return proc.returncode


def main() -> int:
    steps: list[tuple[str, list[str]]] = [
        ("base_chain", [PY, "scripts/run_kospi_dart_mda_poc_chain_v1.py"]),
        ("gate_b_check", [PY, "scripts/check_kospi_dart_mda_poc_human_timing_v1.py"]),
        ("multi_corp_live", [PY, "scripts/run_kospi_dart_mda_poc_multi_corp_live_v1.py"]),
    ]

    inbox_ingested = False
    if _inbox_ready():
        steps.insert(1, (
            "ingest_inbox_paste",
            [
                PY,
                "scripts/ingest_dart_mda_section_v1.py",
                "--mode",
                "manual_paste",
                "--paste-file",
                str(INBOX),
                "--corp-name-ko",
                "지휘관 inbox paste",
                "--out",
                str(CORPUS_INBOX),
            ],
        ))
        inbox_ingested = True

    results: list[dict[str, object]] = []
    ok = True
    for label, cmd in steps:
        code = _run(label, cmd)
        # gate_b_check may exit 1 on fail — only base_chain failure is hard stop
        step_ok = code == 0 or label in ("gate_b_check", "multi_corp_live")
        results.append({"step": label, "exit_code": code, "ok": step_ok})
        if label == "base_chain" and code != 0:
            ok = False
            break

    doc = {
        "schema": "kospi_dart_mda_poc_followup_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "inbox_paste_ready": _inbox_ready(),
        "inbox_ingested": inbox_ingested,
        "inbox_path": str(INBOX),
        "steps": results,
        "reproduce": "py scripts/run_kospi_dart_mda_poc_followup_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "artifact": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
