#!/usr/bin/env python3
"""Chain: glass/blur gate → Playwright A/B → commander visual → readiness."""
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
GATE_SCRIPT = ROOT / "scripts/check_trust_composition_glass_blur_experiment_v1.py"
PLAYWRIGHT = ROOT / "scripts/capture_trust_composition_glass_blur_ab_playwright_v1.mjs"
RECORD = ROOT / "scripts/record_trust_composition_glass_blur_commander_visual_v1.py"
BUILDER = ROOT / "scripts/build_trust_composition_glass_blur_readiness_v1.py"
READINESS = ROOT / "reports/trust_composition_glass_blur_readiness_v1_latest.json"
PYTEST = ROOT / "tests/test_trust_composition_glass_blur_commander_visual_v1.py"
FIGMA_PACK = ROOT / "scripts/build_clinic_loi_figma_reverse_sync_pack_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, cwd: Path | None = None, env_extra: dict[str, str] | None = None) -> dict[str, Any]:
    import os

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return {"cmd": cmd, "exit_code": proc.returncode, "ok": proc.returncode == 0, "tail": tail[-3:]}


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-figma-pack", action="store_true")
    ap.add_argument(
        "--verdict",
        choices=("prefer_flat_baseline", "glass_ok_hub_only", "fail"),
        default="prefer_flat_baseline",
    )
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    steps["gate"] = _run([sys.executable, str(GATE_SCRIPT)])
    ok = ok and steps["gate"]["ok"]

    steps["playwright_ab"] = _run(
        ["node", str(PLAYWRIGHT)],
        cwd=MKM_LIFE,
        env_extra={"MKM_WORKSPACE_ROOT": str(ROOT)},
    )
    ok = ok and steps["playwright_ab"]["ok"]
    pw_doc = _read(ROOT / "reports/trust_composition_glass_blur_playwright_v1_latest.json")
    if not pw_doc or not pw_doc.get("capture_ok"):
        ok = False

    steps["commander_visual"] = _run(
        [sys.executable, str(RECORD), "--verdict", args.verdict]
    )
    ok = ok and steps["commander_visual"]["ok"]

    steps["readiness"] = _run([sys.executable, str(BUILDER)])
    ok = ok and steps["readiness"]["ok"]

    if not args.skip_figma_pack and FIGMA_PACK.is_file():
        steps["figma_pack"] = _run([sys.executable, str(FIGMA_PACK)])
        ok = ok and steps["figma_pack"]["ok"]

    if not args.skip_pytest and PYTEST.is_file():
        steps["pytest"] = _run([sys.executable, "-m", "pytest", str(PYTEST), "-q"])
        ok = ok and steps["pytest"]["ok"]

    readiness: dict[str, Any] = {}
    if READINESS.is_file():
        readiness = json.loads(READINESS.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "trust_composition_glass_blur_commander_visual_chain_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "experiment_ready": readiness.get("experiment_ready"),
        "ab_verdict": readiness.get("ab_verdict"),
        "verdict_ko": readiness.get("verdict_ko"),
        "steps": steps,
    }
    out = ROOT / "reports/trust_composition_glass_blur_commander_visual_chain_v1_latest.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "experiment_ready": readiness.get("experiment_ready")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
