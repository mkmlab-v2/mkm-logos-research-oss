#!/usr/bin/env python3
"""Chain: live DNS/deploy axis isolation probe + optional offline pytest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "scripts/probe_mkm_deployment_axis_isolation_v1.py"
OUT = ROOT / "reports/mkm_deployment_axis_isolation_chain_v1_latest.json"
PROBE_OUT = ROOT / "reports/mkm_deployment_axis_isolation_probe_latest.json"
PYTEST = ROOT / "tests/test_probe_mkm_deployment_axis_isolation_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "tail": tail[-5:] if tail else [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default="core", choices=["core", "extended", "full"])
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    steps["probe"] = _run(
        [sys.executable, str(PROBE), "--profile", args.profile, "--out", str(PROBE_OUT)]
    )
    ok = ok and steps["probe"]["ok"]

    if not args.skip_pytest and PYTEST.is_file():
        steps["pytest"] = _run([sys.executable, "-m", "pytest", str(PYTEST), "-q"])
        ok = ok and steps["pytest"]["ok"]

    probe_doc: dict[str, Any] = {}
    if PROBE_OUT.is_file():
        probe_doc = json.loads(PROBE_OUT.read_text(encoding="utf-8"))

    doc = {
        "schema": "mkm_deployment_axis_isolation_chain_v1",
        "generated_at_utc": _utc(),
        "profile": args.profile,
        "ok": ok,
        "probe_all_ok": probe_doc.get("all_ok"),
        "mkmlife_cf_ok": probe_doc.get("mkmlife_cf_ok"),
        "jema_logos_dns_ok": probe_doc.get("jema_logos_dns_ok"),
        "probe_artifact": str(PROBE_OUT.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
