#!/usr/bin/env python3
"""Optional dependency probe for LocalLock P1.5 Playwright browser helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "local_lock_browser_deps_v1_latest.json"
BROWSER_SCRIPT = ROOT / "scripts" / "local_lock_browser_open_v1.py"


def main() -> int:
    doc: dict = {
        "schema": "local_lock_browser_deps_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "checks": {},
    }
    ok = True

    doc["checks"]["browser_script_exists"] = {"ok": BROWSER_SCRIPT.is_file()}
    ok = ok and doc["checks"]["browser_script_exists"]["ok"]

    try:
        import playwright  # type: ignore

        version = getattr(playwright, "__version__", "unknown")
        doc["checks"]["playwright_import"] = {"ok": True, "version": version}
    except ImportError as exc:
        doc["checks"]["playwright_import"] = {
            "ok": False,
            "error": str(exc),
            "install_hint": "py -m pip install playwright && py -m playwright install chrome",
        }
        ok = False

    doc["ok"] = ok
    doc["reproduce"] = "py scripts/check_local_lock_browser_deps_v1.py"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
