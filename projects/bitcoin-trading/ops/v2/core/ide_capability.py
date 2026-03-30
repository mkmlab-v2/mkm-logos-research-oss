from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class IdeCapability(BaseModel):
    timestamp_utc: str
    os: str
    python_version: str
    node_version: str | None = None
    npm_version: str | None = None
    langgraph_installed: bool = False
    pydantic_installed: bool = False
    pm2_available: bool = False
    notes: list[str] = Field(default_factory=list)


def _cmd_output(cmd: list[str]) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if proc.returncode == 0:
            return (proc.stdout or proc.stderr).strip()
    except Exception:
        return None
    return None


def detect_ide_capability() -> dict:
    notes: list[str] = []

    py = _cmd_output(["python", "--version"]) or "unknown"
    node = _cmd_output(["node", "-v"])
    npm = _cmd_output(["npm", "-v"])

    try:
        import importlib.util as importlib_util

        langgraph_installed = bool(importlib_util.find_spec("langgraph"))
        pydantic_installed = bool(importlib_util.find_spec("pydantic"))
    except Exception:
        langgraph_installed = False
        pydantic_installed = False

    pm2_available = shutil.which("pm2") is not None
    if pm2_available and node and node.startswith("v24"):
        notes.append("PM2 may fail on Node v24 in this environment (pipe EPERM observed)")

    cap = IdeCapability(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        os="windows",
        python_version=py,
        node_version=node,
        npm_version=npm,
        langgraph_installed=langgraph_installed,
        pydantic_installed=pydantic_installed,
        pm2_available=pm2_available,
        notes=notes,
    )
    return cap.model_dump(mode="json")


def save_capability(output_path: Path) -> dict:
    payload = detect_ide_capability()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
