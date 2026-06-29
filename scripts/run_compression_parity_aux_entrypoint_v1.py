#!/usr/bin/env python3
"""Aux share entrypoint (standalone): resolve Python 3.11/3.12 and run parity probe."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_FALLBACK_EXES = (
    Path(r"C:\Python311\python.exe"),
    Path(r"C:\Program Files\Python311\python.exe"),
    Path(r"C:\Python312\python.exe"),
    Path(r"C:\Program Files\Python312\python.exe"),
)
_LINE_RE = re.compile(r"^(-\S+)\s+\*?\s*(.+)$")
_PREFERRED = ((3, 11), (3, 12))


def _workspace_root() -> Path:
    return Path(os.environ.get("MKM_WORKSPACE_ROOT", r"C:\workspace")).resolve()


def _share_dir() -> Path:
    return Path(__file__).resolve().parent


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


def _resolve_parity_python_exe() -> tuple[Path | None, list[str], tuple[int, int] | None]:
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
        if ver is None or ver not in _PREFERRED:
            continue
        found.append((_PREFERRED.index(ver), exe, ver))
    for exe in _FALLBACK_EXES:
        ver = _version_tuple(exe)
        if ver is not None and ver in _PREFERRED:
            found.append((_PREFERRED.index(ver), exe, ver))
    if not found:
        return None, broken, None
    found.sort(key=lambda item: (item[0], str(item[1])))
    _, exe, ver = found[0]
    return exe, broken, ver


def main() -> int:
    workspace = _workspace_root()
    share = _share_dir()
    out = share / "compression_cross_host_parity_aux_probe_v1_latest.json"
    probe = workspace / "scripts/run_compression_cross_host_parity_probe_v1.py"
    if not probe.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"missing probe script: {probe}",
                    "hint": "Run COPY_WORKSPACE_BUNDLE.cmd from share first",
                }
            ),
            file=sys.stderr,
        )
        return 1

    py_exe, broken, py_ver = _resolve_parity_python_exe()
    if py_exe is None:
        proc = subprocess.run(["py", "-0p"], capture_output=True, text=True, check=False)
        print("[FAIL] No working Python 3.11/3.12 for parity.", file=sys.stderr)
        if broken:
            print("[HINT] Broken 3.11 path on disk:", file=sys.stderr)
            for p in broken:
                print(f"  - {p}", file=sys.stderr)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        return 1

    subprocess.run(
        [str(py_exe), "-m", "pip", "install", "tiktoken", "pytest", "fastapi", "httpx", "-q"],
        cwd=workspace,
        check=False,
    )

    env = os.environ.copy()
    env["PYTHONOPTIMIZE"] = "0"
    env["MKM_WORKSPACE_ROOT"] = str(workspace)
    proc = subprocess.run(
        [str(py_exe), str(probe), "--host-label", "aux", "--out", str(out)],
        cwd=workspace,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode
    if out.is_file():
        try:
            doc = json.loads(out.read_text(encoding="utf-8-sig"))
            doc["python_executable"] = str(py_exe).replace("\\", "/")
            if py_ver:
                doc["python_version_used"] = f"{py_ver[0]}.{py_ver[1]}"
            if broken:
                doc["broken_registered_python311_paths"] = broken
            out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out),
                "python_executable": str(py_exe),
                "python_version_used": f"{py_ver[0]}.{py_ver[1]}" if py_ver else None,
                "status": "ok",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
