#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live trading wrapper: load `.env` in a fixed order, then exec the 24h daemon.

Order (later steps override keys from earlier files when python-dotenv is used):
  1) ``<project_root>/.env`` — repo checkout defaults (non-secret templates).
  2) ``/opt/bitcoin-trading/.env`` on POSIX if it exists and is not the same file as (1).
  3) ``Path.cwd() / ".env"`` with override=True — Cursor workspace / operator cwd wins.

Then replaces this process with ``scripts/start_24h_daemon.py`` so singleton lock
and PM2 argv stay aligned with the SSOT daemon entrypoint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _load_dotenv_chain(project_root: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    seen: set[str] = set()

    def _one(path: Path, *, override: bool) -> None:
        if not path.is_file():
            return
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            return
        load_dotenv(path, override=override)
        seen.add(key)

    _one(project_root / ".env", override=False)
    if os.name != "nt":
        deploy = Path("/opt/bitcoin-trading/.env")
        _one(deploy, override=False)
    _one(Path.cwd() / ".env", override=True)


def main() -> None:
    project_root = Path(__file__).resolve().parent
    _load_dotenv_chain(project_root)
    daemon = project_root / "scripts" / "start_24h_daemon.py"
    if not daemon.is_file():
        print(f"ERROR: missing daemon script: {daemon}", file=sys.stderr)
        sys.exit(2)
    os.environ.setdefault("DISABLE_QDRANT", "true")
    os.execv(sys.executable, [sys.executable, str(daemon), *sys.argv[1:]])


if __name__ == "__main__":
    main()
