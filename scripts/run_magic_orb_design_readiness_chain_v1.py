#!/usr/bin/env python3
"""Chain: Playwright design capture + engineering probe merge + optional pytest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MKM_LIFE = ROOT / "projects/mkm/mkm-life"
PLAYWRIGHT = MKM_LIFE / "scripts/capture-magic-orb-design-readiness-playwright.mjs"
BUILDER = ROOT / "scripts/build_magic_orb_design_readiness_v1.py"
PROBE = ROOT / "scripts/probe_mkmlife_magic_orb_live_v1.py"
OUT = ROOT / "reports/magic_orb_design_readiness_chain_v1_latest.json"
READINESS = ROOT / "reports/magic_orb_design_readiness_v1_latest.json"
PYTEST = ROOT / "tests/test_magic_orb_design_readiness_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    import os

    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True, check=False, env=merged)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "tail": tail[-5:] if tail else [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-probe", action="store_true", help="reuse existing magic_orb_live_probe_latest.json")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--strict-consumer", action="store_true")
    ap.add_argument(
        "--commander-visual-ok",
        choices=("true", "false", "unset"),
        default="unset",
    )
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    if not args.skip_probe:
        steps["engineering_probe"] = _run(
            [sys.executable, str(PROBE), "--profile", "core"],
            env={"MKM_WORKSPACE_ROOT": str(ROOT)},
        )
        ok = ok and steps["engineering_probe"]["ok"]
    else:
        steps["engineering_probe"] = {"skipped": True, "ok": True}

    steps["playwright_design"] = _run(
        ["node", str(PLAYWRIGHT)],
        cwd=MKM_LIFE,
        env={
            "MKM_WORKSPACE_ROOT": str(ROOT),
            "MKM_DESIGN_READINESS_STRICT": "0",
        },
    )
    ok = ok and steps["playwright_design"]["ok"]

    build_cmd = [sys.executable, str(BUILDER), "--commander-visual-ok", args.commander_visual_ok]
    if args.strict_consumer:
        build_cmd.append("--strict-consumer")
    steps["build_readiness"] = _run(build_cmd)
    ok = ok and steps["build_readiness"]["ok"]

    if not args.skip_pytest and PYTEST.is_file():
        steps["pytest"] = _run([sys.executable, "-m", "pytest", str(PYTEST), "-q"])
        ok = ok and steps["pytest"]["ok"]

    readiness: dict[str, Any] = {}
    if READINESS.is_file():
        readiness = json.loads(READINESS.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "magic_orb_design_readiness_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "consumer_ready": readiness.get("consumer_ready"),
        "engineering_ok": readiness.get("engineering_ok"),
        "design_ok": readiness.get("design_ok"),
        "verdict_ko": readiness.get("verdict_ko"),
        "readiness_artifact": str(READINESS.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} consumer_ready={doc.get('consumer_ready')}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
