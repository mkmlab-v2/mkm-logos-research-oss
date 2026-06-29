#!/usr/bin/env python3
"""Smoke: System2 gate fail fixture with --live --gemini-repair (skips if no API key)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FAIL = ROOT / "docs/final/artifacts/fixtures/mkm_system2_gate_draft_fail_v1.txt"
DEFAULT_OUT = ROOT / "reports/mkm_system2_gemini_repair_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_gemini_key() -> bool:
    return bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draft-file", default=str(DEFAULT_FAIL))
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--force", action="store_true", help="Run even without GEMINI key (deterministic fallback only)")
    args = ap.parse_args()

    has_key = _has_gemini_key()
    doc: dict = {
        "schema": "mkm_system2_gemini_repair_smoke_v1",
        "generated_at_utc": _utc(),
        "gemini_key_present": has_key,
        "skipped": False,
    }

    if not has_key and not args.force:
        doc.update({"ok": True, "skipped": True, "reason": "no_gemini_key"})
        Path(args.out_json).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(doc))
        return 0

    cmd = [
        sys.executable,
        str(ROOT / "scripts/mkm_system2_self_correction_gate_mvp_v1.py"),
        "run",
        "--draft-file",
        args.draft_file,
        "--live",
        "--gemini-repair",
        "--max-retries",
        str(args.max_retries),
    ]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    gate_summary: dict = {}
    try:
        gate_summary = json.loads((cp.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        gate_summary = {"raw": (cp.stdout or "")[-200:]}

    report_path = ROOT / "reports/mkm_system2_self_correction_gate_mvp_v1_latest.json"
    repair_engine = None
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        attempts = report.get("attempts") or []
        for att in attempts:
            if att.get("repair"):
                repair_engine = att["repair"]
                break
        doc["gate_all_pass"] = report.get("all_pass")
        doc["draft_final_excerpt"] = (report.get("draft_final") or "")[:240]

    doc.update(
        {
            "ok": cp.returncode == 0,
            "cmd": cmd,
            "exit_code": cp.returncode,
            "gate_summary": gate_summary,
            "repair_engine": repair_engine,
        }
    )
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "skipped": doc["skipped"], "out_json": args.out_json}))
    return 0 if doc["ok"] or doc.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
