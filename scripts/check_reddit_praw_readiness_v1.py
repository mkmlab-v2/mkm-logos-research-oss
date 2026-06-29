#!/usr/bin/env python3
"""Smoke Reddit PRAW credentials + r/LocalLLM reachability (no submit)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/reddit_praw_readiness_v1_latest.json"
SCRIPT = ROOT / "scripts/post_reddit_praw_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--dry-run", "--pack", "bible_topology"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    doc: dict = {
        "schema": "reddit_praw_readiness_v1",
        "generated_at_utc": _utc(),
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "ok": proc.returncode == 0,
    }
    if proc.stdout.strip():
        try:
            doc["parsed"] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            pass
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "exit_code": proc.returncode}, ensure_ascii=False))
    return 0 if doc["ok"] else proc.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
