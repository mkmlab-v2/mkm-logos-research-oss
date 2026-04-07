#!/usr/bin/env python3
"""Write reports/aistudio_mcp_env_diagnosis.json — key lengths only, no secrets."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None  # type: ignore

REPO = Path(__file__).resolve().parents[1]
DOTENV = REPO / ".env"
OUT = REPO / "reports" / "aistudio_mcp_env_diagnosis.json"


def _len_dotenv_gemini() -> int | None:
    if not DOTENV.is_file():
        return None
    for line in DOTENV.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*GEMINI_API_KEY\s*=\s*(.*)$", line)
        if not m:
            continue
        v = m.group(1).strip().strip('"').strip("'")
        return len(v) if v else 0
    return None


def _len_user_gemini() -> int | None:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
            v, _ = winreg.QueryValueEx(k, "GEMINI_API_KEY")
            return len(v) if isinstance(v, str) and v else 0
    except OSError:
        return None


def main() -> int:
    ld = _len_dotenv_gemini()
    lu = _len_user_gemini()
    payload = {
        "schema": "aistudio_mcp_env_diagnosis_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "dotenv_path": str(DOTENV),
        "dotenv_exists": DOTENV.is_file(),
        "gemini_api_key_len_dotenv": ld,
        "gemini_api_key_len_user_registry": lu,
        "dotenv_user_len_match": ld is not None and lu is not None and ld == lu,
        "launcher_script": str(REPO / "scripts" / "run_aistudio_mcp.ps1"),
        "launcher_exists": (REPO / "scripts" / "run_aistudio_mcp.ps1").is_file(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
