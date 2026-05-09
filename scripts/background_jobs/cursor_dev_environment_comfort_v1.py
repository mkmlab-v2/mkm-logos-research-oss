#!/usr/bin/env python3
"""
Fusion snapshot: Cursor IDE native perf vs dev productivity + workspace hygiene.

- IDE responsiveness (Electron/RAM) is NOT changed by MKM repo work; this script only reports hygiene signals.
- Dev productivity levers: Fact-Lock paths, automation, smaller noisy working trees.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path("C:/workspace")
OUT_JSON = WORKSPACE / "docs/final/artifacts/cursor_dev_environment_comfort_latest.json"
OUT_MD = WORKSPACE / "docs/final/artifacts/cursor_dev_environment_comfort_latest.md"
CURSORIGNORE = WORKSPACE / ".cursorignore"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_porcelain_lines() -> tuple[int, str | None]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(WORKSPACE), "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return -1, str(e)
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return len(lines), None if proc.returncode == 0 else f"git_exit_{proc.returncode}"


def _cursorignore_scan() -> dict[str, Any]:
    if not CURSORIGNORE.is_file():
        return {"exists": False, "bytes": 0, "has_node_modules_rule": False}
    raw = CURSORIGNORE.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    return {
        "exists": True,
        "bytes": len(raw),
        "line_count": len(text.splitlines()),
        "has_node_modules_rule": bool(re.search(r"node_modules", text, re.I)),
        "has_venv_rule": bool(re.search(r"\.venv|venv", text, re.I)),
    }


def _comfort_level(porcelain_n: int) -> str:
    if porcelain_n < 0:
        return "UNKNOWN"
    if porcelain_n <= 200:
        return "GREEN"
    if porcelain_n <= 1200:
        return "YELLOW"
    return "RED"


def main() -> int:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    n_lines, git_err = _git_porcelain_lines()
    ci = _cursorignore_scan()
    level = _comfort_level(n_lines)

    payload: dict[str, Any] = {
        "schema": "cursor_dev_environment_comfort_v1",
        "generated_at_utc": _utc_now(),
        "fusion": {
            "ide_native_performance": (
                "MKM/monorepo automation does not speed up Cursor Electron or the editor binary; "
                "RAM/SSD/extensions/agent tabs dominate raw IDE responsiveness."
            ),
            "dev_productivity": (
                "Rules, scripts, Fact-Lock paths, and cleaner git/index scope reduce retries and wasted turns — "
                "that is indirect 'speed', not FPS for the IDE."
            ),
            "this_report_measures": (
                ".cursorignore presence, git porcelain noise (index/UI friction proxy). "
                "Optional: run_full_health with -IncludeCursorDevEnvironmentComfort."
            ),
        },
        "signals": {
            "git_porcelain_line_count": n_lines,
            "git_error": git_err,
            "cursorignore": ci,
            "comfort_level": level,
        },
        "recommendations": [],
    }

    if not ci.get("exists"):
        payload["recommendations"].append("Add root .cursorignore to slim Cursor indexing (see repo template).")
    elif not ci.get("has_node_modules_rule"):
        payload["recommendations"].append("Ensure .cursorignore excludes **/node_modules/.")

    if n_lines > 1200:
        payload["recommendations"].append(
            "Working tree is very noisy: restore timestamp-only files, commit intentional changes, or extend .gitignore."
        )
    elif n_lines > 200:
        payload["recommendations"].append(
            "Moderate porcelain noise: periodic git restore on generated *_latest artifacts if policy allows."
        )

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md = "\n".join(
        [
            "# Cursor dev environment comfort",
            "",
            f"- generated_at_utc: `{payload['generated_at_utc']}`",
            f"- comfort_level: `{level}`",
            f"- git_porcelain_lines: `{n_lines}`",
            f"- cursorignore_exists: `{ci.get('exists')}`",
        ]
    )
    OUT_MD.write_text(md + "\n", encoding="utf-8")
    try:
        out_rel = str(OUT_JSON.relative_to(WORKSPACE)).replace("\\", "/")
    except ValueError:
        out_rel = str(OUT_JSON)
    print(json.dumps({"out": out_rel, "comfort_level": level, "porcelain_lines": n_lines}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
