#!/usr/bin/env python3
"""Verify PersonaDiary native shell hypo scaffold paths and schema (research_only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "docs/final/schemas/personadiary_native_shell_hypo_v1.schema.json"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/personadiary_native_shell_hypo_v1.example.json"
SHELL_DIR = ROOT / "projects/no1kmedi/personadiary-native-hypo-v1"
DEFAULT_OUT = ROOT / "reports/personadiary_native_shell_hypo_readiness_latest.json"

REQUIRED_SHELL_FILES = (
    SHELL_DIR / "package.json",
    SHELL_DIR / "capacitor.config.json",
    SHELL_DIR / "www/index.html",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check-bootstrap",
        action="store_true",
        help="Require node_modules + android/ after Invoke-PersonadiaryNativeShellHypoBootstrap_v1.ps1",
    )
    parser.add_argument(
        "--check-ios",
        action="store_true",
        help="Require ios/ after bootstrap with -Platform Ios or Both",
    )
    args = parser.parse_args()

    errors: list[str] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=fixture, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"fixture_invalid: {exc.message[:200]}")

    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_SHELL_FILES if not p.is_file()]
    if missing:
        errors.extend([f"missing_file:{m}" for m in missing])

    node_modules_ok = (SHELL_DIR / "node_modules").is_dir()
    android_ok = (SHELL_DIR / "android").is_dir()
    ios_ok = (SHELL_DIR / "ios").is_dir()
    bootstrap_json = ROOT / "reports/personadiary_native_shell_hypo_bootstrap_latest.json"
    bootstrap_ok = bootstrap_json.is_file()
    copy_contract = ROOT / "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json"
    if not copy_contract.is_file():
        errors.append("missing_file:docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json")

    if args.check_bootstrap:
        if not node_modules_ok:
            errors.append("bootstrap_missing:node_modules (run Invoke-PersonadiaryNativeShellHypoBootstrap_v1.ps1)")
        if not android_ok:
            errors.append("bootstrap_missing:android (cap add android failed or skipped)")

    if args.check_ios:
        if not ios_ok:
            errors.append("bootstrap_missing:ios (run Invoke-PersonadiaryNativeShellHypoBootstrap_v1.ps1 -Platform Both)")

    report = {
        "schema": "personadiary_native_shell_hypo_readiness_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "fixture_path": str(FIXTURE.relative_to(ROOT)),
        "shell_dir": str(SHELL_DIR.relative_to(ROOT)),
        "copy_contract_ok": copy_contract.is_file(),
        "required_files_ok": len(missing) == 0,
        "missing_files": missing,
        "push_enabled_fixture": fixture.get("push_enabled"),
        "node_modules_ok": node_modules_ok,
        "android_dir_ok": android_ok,
        "ios_dir_ok": ios_ok,
        "bootstrap_report_present": bootstrap_ok,
        "check_bootstrap": args.check_bootstrap,
        "check_ios": args.check_ios,
        "ok": len(errors) == 0,
        "errors": errors,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
