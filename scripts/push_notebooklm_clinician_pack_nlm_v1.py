#!/usr/bin/env python3
"""Push clinician pack via nlm CLI (preserves source titles; prefer over MCP text paste).

SSOT pack: reports/notebooklm_clinician_sync_pack_v1/
URL: reports/notebooklm_clinician_notebook_url_v1.txt
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "reports" / "notebooklm_clinician_sync_pack_v1"
URL_FILE = ROOT / "reports" / "notebooklm_clinician_notebook_url_v1.txt"
OUT = ROOT / "reports" / "notebooklm_clinician_push_nlm_latest.json"


def _notebook_id() -> str:
    url = URL_FILE.read_text(encoding="utf-8").strip()
    m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
    if not m:
        raise SystemExit(f"bad notebook URL in {URL_FILE}")
    return m.group(1)


def _add_file(nb: str, path: Path, title: str) -> dict:
    if path.suffix.lower() == ".json":
        r = subprocess.run(
            ["nlm", "source", "add", nb, "--text", path.read_text(encoding="utf-8"), "--title", title, "--wait"],
            capture_output=True,
            text=True,
        )
    else:
        r = subprocess.run(
            ["nlm", "source", "add", nb, "--file", str(path), "--title", title, "--wait"],
            capture_output=True,
            text=True,
        )
    return {"title": title, "exit_code": r.returncode, "stderr": (r.stderr or r.stdout)[-300:] if r.returncode else None}


def main() -> int:
    if not (PACK / "index.json").is_file():
        raise SystemExit("run build_notebooklm_clinician_sync_pack_v1.py first")
    nb = _notebook_id()
    files = json.loads((PACK / "index.json").read_text(encoding="utf-8"))["files"]
    rows = [_add_file(nb, PACK / name, name) for name in files if isinstance(name, str)]
    doc = {"schema": "notebooklm_clinician_push_nlm_latest", "notebook_id": nb, "rows": rows}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fail = sum(1 for r in rows if r["exit_code"] != 0)
    print(json.dumps({"notebook_id": nb, "ok": len(rows) - fail, "fail": fail, "out": str(OUT)}, ensure_ascii=False))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
