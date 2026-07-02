#!/usr/bin/env python3
"""Logos inquiry public beta pack v1 — text Q&A surface + OSS verify (no graphics/payment)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core.logos_inquiry_payapp_e2e_v1 import validate_scaffold  # noqa: E402

OUT = ROOT / "reports/logos_inquiry_beta_pack_v1_latest.json"
PY = sys.executable
CONTRACT = ROOT / "docs/final/artifacts/logos_inquiry_beta_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-oss-verify", action="store_true")
    ap.add_argument("--skip-handoff", action="store_true")
    args = ap.parse_args()

    steps: list[dict] = []
    errors: list[str] = []
    contract: dict = {}

    if not CONTRACT.is_file():
        errors.append(f"missing contract: {CONTRACT.relative_to(ROOT)}")
    else:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("graphics_studio", {}).get("status") != "deferred":
            errors.append("graphics_studio must be deferred in beta contract")

    page = (ROOT / "projects/no1kmedi/src/app/logos-research/page.tsx").read_text(encoding="utf-8")
    if "LogosGraphStudioHeroInlineDemo" in page:
        errors.append("homepage still imports graph hero demo")
    if "LogosResearchInquiryBetaHome" not in page:
        errors.append("homepage missing LogosResearchInquiryBetaHome")

    if not args.skip_handoff:
        proc = subprocess.run(
            [PY, str(ROOT / "scripts/build_logos_jema_ai_research_handoff_v1.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        steps.append({"name": "rebuild_handoff", "ok": proc.returncode == 0, "exit_code": proc.returncode})
        if proc.returncode != 0:
            errors.append("handoff rebuild failed")

    proc = subprocess.run(
        [PY, str(ROOT / "scripts/check_logos_inquiry_s4_allowlist_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    steps.append({"name": "s4_allowlist", "ok": proc.returncode == 0, "exit_code": proc.returncode})
    if proc.returncode != 0:
        errors.append("s4 allowlist check failed")

    proc = subprocess.run(
        [PY, str(ROOT / "scripts/check_logos_research_surface_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    steps.append({"name": "surface_check", "ok": proc.returncode == 0, "exit_code": proc.returncode})
    if proc.returncode != 0:
        errors.append("surface check failed")

    scaffold = validate_scaffold(root=ROOT)

    contract_payment = (contract or {}).get("payment") or {}
    if contract_payment.get("status") != "deferred":
        errors.append("beta contract payment.status must be deferred")

    for rel in (
        "docs/final/artifacts/logos_oss_github_issue_template_beta_feedback_v1.yml",
        "docs/final/artifacts/logos_oss_third_party_repro_checklist_v1_latest.json",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"missing beta/oss artifact: {rel}")

    if not args.skip_oss_verify:
        proc = subprocess.run(
            [PY, str(ROOT / "scripts/build_logos_oss_public_export_bundle_v1.py"), "--verify-only"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        steps.append({"name": "oss_verify_only", "ok": proc.returncode == 0, "exit_code": proc.returncode})
        if proc.returncode != 0:
            errors.append("oss export verify-only failed")

    proc = subprocess.run(
        [PY, str(ROOT / "scripts/check_logos_oss_beta_recruitment_gate_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    steps.append({"name": "recruitment_gate", "ok": proc.returncode == 0, "exit_code": proc.returncode})
    if proc.returncode != 0:
        errors.append("beta recruitment gate failed")

    if not args.skip_pytest:
        proc = subprocess.run(
            [
                PY,
                "-m",
                "pytest",
                "tests/test_logos_inquiry_report_v1.py",
                "tests/test_logos_inquiry_stream_v1.py",
                "tests/test_logos_research_surface_v1.py",
                "-q",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        steps.append({"name": "pytest", "ok": proc.returncode == 0, "exit_code": proc.returncode})
        if proc.returncode != 0:
            errors.append("pytest failed")

    ok = not errors and scaffold.get("ok")
    report = {
        "schema": "logos_inquiry_beta_pack_v1",
        "ok": ok,
        "generated_at_utc": _utc(),
        "errors": errors,
        "steps": steps,
        "payment_status": contract_payment.get("status"),
        "payment_policy": contract_payment.get("policy"),
        "beta_contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "github_repo": "https://github.com/mkmlab-v2/mkm-logos-research-oss",
        "reproduce": "py scripts/run_logos_inquiry_beta_pack_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "errors": errors}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
