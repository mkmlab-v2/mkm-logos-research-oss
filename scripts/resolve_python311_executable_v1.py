#!/usr/bin/env python3
"""Resolve a working Python exe for compression parity (prefer 3.11, then 3.12)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FALLBACK_EXES = (
    Path(r"C:\Python311\python.exe"),
    Path(r"C:\Program Files\Python311\python.exe"),
    Path(r"C:\Python312\python.exe"),
    Path(r"C:\Program Files\Python312\python.exe"),
)
_LINE_RE = re.compile(r"^(-\S+)\s+\*?\s*(.+)$")
PREFERRED_VERSIONS = ((3, 11), (3, 12))


def _version_tuple(exe: Path) -> tuple[int, int] | None:
    if not exe.is_file():
        return None
    proc = subprocess.run(
        [str(exe), "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    parts = (proc.stdout or "").strip().split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _priority(ver: tuple[int, int]) -> int:
    try:
        return PREFERRED_VERSIONS.index(ver)
    except ValueError:
        return 99


def resolve_parity_python_exe() -> tuple[Path | None, list[str], tuple[int, int] | None]:
    """Return (exe, broken_311_paths, version_tuple)."""
    broken: list[str] = []
    found: list[tuple[int, Path, tuple[int, int]]] = []

    proc = subprocess.run(["py", "-0p"], capture_output=True, text=True, check=False)
    for raw in (proc.stdout or "").splitlines():
        line = raw.strip()
        m = _LINE_RE.match(line)
        if not m:
            continue
        exe = Path(m.group(2).strip())
        if "3.11" in line and not exe.is_file():
            broken.append(str(exe))
            continue
        ver = _version_tuple(exe)
        if ver is None or ver not in PREFERRED_VERSIONS:
            continue
        found.append((_priority(ver), exe, ver))

    for exe in FALLBACK_EXES:
        ver = _version_tuple(exe)
        if ver is not None and ver in PREFERRED_VERSIONS:
            found.append((_priority(ver), exe, ver))

    if not found:
        return None, broken, None
    found.sort(key=lambda item: (item[0], str(item[1])))
    _, exe, ver = found[0]
    return exe, broken, ver


# Back-compat alias
def resolve_python311_exe() -> tuple[Path | None, list[str]]:
    exe, broken, ver = resolve_parity_python_exe()
    if exe is not None and ver == (3, 11):
        return exe, broken
    if exe is not None and ver == (3, 12):
        return exe, broken
    return None, broken


def main() -> int:
    exe, broken, ver = resolve_parity_python_exe()
    if exe is None:
        if broken:
            print("broken_paths=" + "|".join(broken), file=sys.stderr)
        return 1
    print(str(exe), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
