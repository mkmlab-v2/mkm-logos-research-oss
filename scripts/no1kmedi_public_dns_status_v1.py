#!/usr/bin/env python3
"""Read or refresh no1kmedi public DNS/HTTPS status (no CF API token)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "no1kmedi_public_dns_verify_latest.json"
VERIFY_SCRIPT = ROOT / "scripts" / "verify_no1kmedi_public_dns_v1.py"


def load_public_dns_status(*, refresh: bool = False) -> dict:
    if refresh or not OUT.is_file():
        subprocess.run([sys.executable, str(VERIFY_SCRIPT)], cwd=ROOT, check=False)
    if not OUT.is_file():
        return {"all_ok": False, "missing": True}
    return json.loads(OUT.read_text(encoding="utf-8"))


def public_dns_live() -> bool:
    doc = load_public_dns_status(refresh=False)
    return bool(doc.get("all_ok"))


def main() -> int:
    refresh = "--refresh" in sys.argv
    doc = load_public_dns_status(refresh=refresh)
    wrap = {
        "schema": "no1kmedi_public_dns_status_v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "public_dns_live": bool(doc.get("all_ok")),
        "verify": doc,
    }
    print(json.dumps(wrap, indent=2))
    return 0 if wrap["public_dns_live"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
