#!/usr/bin/env python3
"""Solo OSS public release readiness — LICENSE, README disclaimer, secret wall.

Does NOT push GitHub. Does NOT require counsel_signoff.

  py scripts/check_mkm_solo_oss_release_readiness_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json"
OUT = ROOT / "reports/mkm_solo_oss_release_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    errors: list[str] = []
    checks: dict[str, bool] = {}

    license_path = ROOT / "LICENSE"
    checks["license_mit_present"] = license_path.is_file()
    if not checks["license_mit_present"]:
        errors.append("missing LICENSE (MIT)")

    readme = ROOT / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    checks["readme_present"] = bool(readme_text.strip())
    for needle in (
        "MIT License",
        "Disclaimer",
        "research",
        "not investment",
        "Measured (this repo)",
        "external research",
        "Install ladder",
        "Blind Cursor",
        "Orchestrated Cursor",
        "Show HN",
    ):
        key = f"readme_contains_{needle.replace(' ', '_').lower()}"
        checks[key] = needle.lower() in readme_text.lower()
        if not checks[key]:
            errors.append(f"README missing: {needle!r}")

    gitignore = ROOT / ".gitignore"
    gi = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    for secret in (".env", ".env.local", "MISSION_LOG.md"):
        checks[f"gitignore_blocks_{secret.replace('.', '')}"] = secret in gi
        if secret not in gi:
            errors.append(f".gitignore missing block: {secret}")

    checks["policy_present"] = POLICY.is_file()
    if not checks["policy_present"]:
        errors.append(f"missing policy: {POLICY}")

    for rel in (
        "SECURITY.md",
        ".gitleaks.toml",
        ".pre-commit-config.yaml",
        "scripts/check_mkm_secret_patterns_v1.py",
        "scripts/run_mkm_secret_scan_v1.ps1",
        "scripts/check_hardcoded_workspace_paths_v1.py",
    ):
        p = ROOT / rel
        key = f"present_{rel.replace('/', '_').replace('.', '_')}"
        checks[key] = p.is_file()
        if not checks[key]:
            errors.append(f"missing: {rel}")

    path_audit = subprocess.run(
        [sys.executable, "scripts/check_hardcoded_workspace_paths_v1.py", "--scope", "oss", "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    checks["oss_path_audit_strict"] = path_audit.returncode == 0
    if not checks["oss_path_audit_strict"]:
        errors.append("hardcoded C:\\workspace in OSS scope (run normalize_workspace_paths_v1.py --apply)")

    doc = {
        "schema": "mkm_solo_oss_release_readiness_v1",
        "generated_at_utc": _utc(),
        "ok": not errors,
        "checks": checks,
        "errors": errors,
        "send_gate_scope": {"oss_github_release": "OPEN", "counsel_signoff": "DEPRECATED"},
        "reproduce": "py scripts/check_mkm_solo_oss_release_readiness_v1.py",
        "next_human_step": "scripts/Push-GitHub-Explicit.ps1 -Acknowledge (explicit approval only)",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print(f"OK: solo OSS release readiness -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
