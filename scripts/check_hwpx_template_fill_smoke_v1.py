#!/usr/bin/env python3
"""Smoke: python-hwpx import, template build, fill_by_path, substring verification."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/hwpx_template_fill_smoke_latest.json"
REQ = ROOT / "scripts/requirements-hwpx-poc.txt"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _py() -> str:
    return sys.executable


def _run(cmd: list[str], *, quiet: bool) -> int:
    if quiet:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr or proc.stdout or "")
        return proc.returncode
    return subprocess.call(cmd, cwd=str(ROOT))


def _ensure_python_hwpx(*, quiet: bool) -> dict[str, object]:
    try:
        import hwpx  # noqa: PLC0415

        return {"installed": True, "version": getattr(hwpx, "__version__", "unknown")}
    except ImportError:
        if not REQ.is_file():
            return {"installed": False, "error": f"missing {REQ}"}
        code = _run([_py(), "-m", "pip", "install", "-r", str(REQ)], quiet=quiet)
        if code != 0:
            return {"installed": False, "error": "pip install failed"}
        import hwpx  # noqa: PLC0415

        return {"installed": True, "version": getattr(hwpx, "__version__", "unknown"), "pip_installed": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--skip-pip-install", action="store_true", help="Do not auto-install python-hwpx")
    args = ap.parse_args()

    steps: list[dict[str, object]] = []
    ok = True

    if args.skip_pip_install:
        try:
            import hwpx  # noqa: F401, PLC0415

            dep = {"installed": True, "version": getattr(hwpx, "__version__", "unknown")}
        except ImportError:
            dep = {"installed": False, "error": "python-hwpx missing (--skip-pip-install)"}
            ok = False
    else:
        dep = _ensure_python_hwpx(quiet=args.quiet)
        if not dep.get("installed"):
            ok = False
    steps.append({"step": "python_hwpx", "ok": bool(dep.get("installed")), "detail": dep})

    if ok:
        build_code = _run([_py(), "scripts/build_hwpx_poc_template_v1.py"], quiet=args.quiet)
        steps.append({"step": "build_template", "ok": build_code == 0, "exit_code": build_code})
        ok = ok and build_code == 0

    if ok:
        fill_code = _run([_py(), "scripts/run_hwpx_template_fill_poc_v1.py"], quiet=args.quiet)
        steps.append({"step": "fill_poc", "ok": fill_code == 0, "exit_code": fill_code})
        ok = ok and fill_code == 0

    poc_report = ROOT / "reports/hwpx_poc/hwpx_template_fill_poc_latest.json"
    if ok and poc_report.is_file():
        poc = json.loads(poc_report.read_text(encoding="utf-8"))
        steps.append(
            {
                "step": "fill_report",
                "ok": bool(poc.get("fill_ok")),
                "output_path": poc.get("output_path"),
                "applied_count": (poc.get("fill_result") or {}).get("applied_count"),
            }
        )
        ok = ok and bool(poc.get("fill_ok"))

    doc = {
        "schema": "hwpx_template_fill_smoke_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "boundary_ack": "research_only",
        "smoke_ok": ok,
        "steps": steps,
        "next": "Replace data/btrack/hwpx_poc/slots_v1.example.json and pass --user-template <official.hwpx>",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.quiet:
        print(json.dumps({"smoke_ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
