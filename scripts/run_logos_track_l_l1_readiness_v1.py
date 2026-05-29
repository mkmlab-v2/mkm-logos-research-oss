#!/usr/bin/env python3
"""Track L L1 readiness: L0 pass + Track B Logos policy chain readiness."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
L0_SCRIPT = ROOT / "scripts/run_logos_track_l_l0_readiness_v1.py"
POLICY_SCRIPT = ROOT / "scripts/report_logos_track_b_policy_readiness_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l1_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _run_py(script: Path, *extra: str) -> tuple[int, dict[str, Any] | None]:
    proc = subprocess.run(
        [sys.executable, str(script), *extra],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    artifact: dict[str, Any] | None = None
    if script == L0_SCRIPT:
        p = ROOT / "docs/final/artifacts/logos_track_l_l0_readiness_v1_latest.json"
    elif script == POLICY_SCRIPT:
        p = ROOT / "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"
    else:
        p = None
    if p and p.is_file():
        try:
            artifact = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            artifact = None
    return proc.returncode, artifact


def build_report(*, skip_policy: bool) -> dict[str, Any]:
    l0_rc, l0_art = _run_py(L0_SCRIPT)
    l0_ok = bool(l0_art and l0_art.get("l0_ok") is True and l0_rc == 0)

    policy_rc = 0
    policy_art: dict[str, Any] | None = None
    if not skip_policy:
        policy_rc, policy_art = _run_py(POLICY_SCRIPT)
    policy_ok = bool(policy_art and policy_art.get("overall_ok") is True and policy_rc == 0)

    l1_ok = l0_ok and (policy_ok if not skip_policy else True)
    return {
        "schema": "logos_track_l_l1_readiness_v1",
        "generated_at_utc": _utc_now(),
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
        },
        "l1_ok": l1_ok,
        "checks": {
            "l0": {"exit_code": l0_rc, "l0_ok": l0_ok, "artifact": _rel(ROOT / "docs/final/artifacts/logos_track_l_l0_readiness_v1_latest.json")},
            "track_b_policy": {
                "skipped": skip_policy,
                "exit_code": policy_rc,
                "overall_ok": policy_ok,
                "artifact": _rel(ROOT / "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"),
            },
        },
        "pointer": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md §L1",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Track L L1 readiness bundle")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-policy", action="store_true")
    args = ap.parse_args(argv)

    doc = build_report(skip_policy=args.skip_policy)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["l1_ok"], "wrote": str(out)}, ensure_ascii=False))
    return 0 if doc["l1_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
