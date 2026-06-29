#!/usr/bin/env python3
"""Prepend Cursor reload banner to mkm_chat_resume_pack_latest.md when host hygiene is degraded."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BANNER_START = "> **[!] ATTENTION: Cursor Reload Required**"
ROOT = Path("C:/workspace")
PACK_MD = ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.md"
HYGIENE_JSON = ROOT / "reports/cursor_host_hygiene_latest.json"
DEGRADED_JSON = ROOT / "reports/cursor_perf_degraded.json"

BANNER_TEMPLATE = """{start} — host hygiene degraded ({reasons}). Quit Cursor fully, then **Reload Window** or restart. SSOT: `reports/cursor_host_hygiene_latest.json` · safe cleanup: `scripts/Invoke-CursorStateVscdbJanitor_v1.ps1 -Apply` (Cursor closed).

"""


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _should_alert(hygiene: dict, degraded: dict) -> tuple[bool, str]:
    if degraded.get("degraded") is True or degraded.get("reload_required") is True:
        reasons = degraded.get("reasons") or hygiene.get("reasons") or ["see hygiene json"]
        return True, "; ".join(str(r) for r in reasons[:4])
    if hygiene.get("degraded") is True or hygiene.get("reload_required") is True:
        reasons = hygiene.get("reasons") or ["see hygiene json"]
        return True, "; ".join(str(r) for r in reasons[:4])
    return False, ""


def _strip_existing_banner(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    if lines[0].startswith("> **[!] ATTENTION: Cursor Reload Required**"):
        idx = 0
        while idx < len(lines) and lines[idx].strip():
            idx += 1
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        return "\n".join(lines[idx:])
    return text


def main() -> int:
    hygiene = _read_json(HYGIENE_JSON)
    degraded = _read_json(DEGRADED_JSON)
    alert, reason_text = _should_alert(hygiene, degraded)
    if not alert:
        print("inject: no alert (hygiene ok)")
        return 0

    banner = BANNER_TEMPLATE.format(start=BANNER_START, reasons=reason_text)
    if PACK_MD.is_file():
        body = _strip_existing_banner(PACK_MD.read_text(encoding="utf-8"))
        PACK_MD.write_text(banner + "\n" + body.lstrip("\n"), encoding="utf-8")
        print(f"inject: prepended banner to {PACK_MD}")
    else:
        PACK_MD.parent.mkdir(parents=True, exist_ok=True)
        PACK_MD.write_text(
            banner + "\n# MKM Chat Resume Pack\n\n(host alert only — run build_mkm_chat_resume_pack_v1.py)\n",
            encoding="utf-8",
        )
        print(f"inject: created minimal {PACK_MD}")

    stamp = ROOT / "reports/cursor_host_alert_injected_latest.json"
    stamp.write_text(
        json.dumps(
            {
                "schema": "cursor_host_alert_injected_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pack_md": str(PACK_MD.relative_to(ROOT)).replace("\\", "/"),
                "reasons": reason_text,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
