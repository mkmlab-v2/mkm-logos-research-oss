#!/usr/bin/env python3
"""Validate PersonaDiary Android Intent E2E report (deep link + share · research_only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports/personadiary_android_intent_e2e_latest.json"
DEFAULT_SHOT = ROOT / "reports/personadiary_android_intent_e2e_latest.png"
INVOKE_PS1 = ROOT / "scripts/Invoke-PersonadiaryAndroidIntentE2e_v1.ps1"
PKG = "com.mkmlife.personadiary.hypo"
REQUIRED_PROBE_IDS = ("save_moment_note", "add_reminder", "share_text")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_report(report: dict, *, shot_path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.get("schema") != "personadiary_android_intent_e2e_v1":
        errors.append("schema_mismatch")
    if report.get("package") != PKG:
        errors.append(f"package_expected:{PKG}")
    if not report.get("research_only"):
        errors.append("research_only_false")
    if report.get("hypothesis_tier") != "B":
        errors.append("hypothesis_tier_not_B")

    probes = report.get("probes") or []
    probe_ids = [p.get("id") for p in probes if isinstance(p, dict)]
    for pid in REQUIRED_PROBE_IDS:
        if pid not in probe_ids:
            errors.append(f"missing_probe:{pid}")

    for probe in probes:
        if not isinstance(probe, dict):
            errors.append("probe_not_object")
            continue
        if probe.get("id") in REQUIRED_PROBE_IDS and not probe.get("ok"):
            errors.append(f"probe_failed:{probe.get('id')}")
        if not probe.get("pid"):
            errors.append(f"probe_missing_pid:{probe.get('id')}")

    if not shot_path.is_file():
        errors.append(f"screenshot_missing:{shot_path.relative_to(ROOT)}")
    elif shot_path.stat().st_size < 1000:
        errors.append("screenshot_too_small")

    ok = len(errors) == 0 and bool(report.get("ok"))
    return ok, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--screenshot", type=Path, default=DEFAULT_SHOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--invoke",
        action="store_true",
        help="Run Invoke-PersonadiaryAndroidIntentE2e_v1.ps1 first",
    )
    parser.add_argument("--skip-emulator-start", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()

    if args.invoke:
        if not INVOKE_PS1.is_file():
            print(f"invoke_script_missing: {INVOKE_PS1}", file=sys.stderr)
            return 1
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INVOKE_PS1),
        ]
        if args.skip_emulator_start:
            cmd.append("-SkipEmulatorStart")
        if args.skip_install:
            cmd.append("-SkipInstall")
        proc = subprocess.run(cmd, cwd=ROOT)
        if proc.returncode != 0:
            return proc.returncode

    if not args.report_json.is_file():
        print(f"report_missing: {args.report_json}", file=sys.stderr)
        return 1

    report = json.loads(args.report_json.read_text(encoding="utf-8-sig"))
    ok, errors = validate_report(report, shot_path=args.screenshot)

    out = {
        **report,
        "validated_at_utc": _utc_now(),
        "validation_ok": ok,
        "validation_errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
