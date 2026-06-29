#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B-track [HYPO]: fetch smallest patent-drawing label zip via aihubshell (WSL)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_WSL = "/tmp/aihub_patent_sample"
OUT_WIN = ROOT / "data" / "research" / "btrack" / "samples" / "aihub_raw"
OUT_WSL_MNT = "/mnt/c/workspace/data/research/btrack/samples/aihub_raw"
SHELL = "/mnt/c/Users/PRO/AppData/Local/Temp/aihubshell"
DATASETKEY = 71919
FILEKEY = 567401  # TL_B. 화학·야금_7. 회로도.zip (~8 KB)


def _load_key() -> str:
    key = os.environ.get("AIHUB_API_KEY", "").strip()
    if key:
        return key
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("AIHUB_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("AIHUB_API_KEY missing (.env or env)")


def main() -> int:
    key = _load_key()
    OUT_WIN.mkdir(parents=True, exist_ok=True)
    inner = (
        f"mkdir -p {OUT_WSL} && cd {OUT_WSL} && "
        f"chmod +x {SHELL} && "
        f"{SHELL} -mode d -datasetkey {DATASETKEY} -filekey {FILEKEY} "
        f"-aihubapikey '{key}' && "
        f"mkdir -p {OUT_WSL_MNT} && "
        f"find {OUT_WSL} -name 'TL_*.zip' -exec cp {{}} {OUT_WSL_MNT}/TL_patent_circuit.zip \\;"
    )
    proc = subprocess.run(["wsl", "-e", "bash", "-lc", inner], capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout[-4000:])
    if proc.stderr:
        print(proc.stderr[-4000:], file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
