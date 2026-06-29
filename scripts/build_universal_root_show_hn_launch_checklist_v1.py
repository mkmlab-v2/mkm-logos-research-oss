#!/usr/bin/env python3
"""UR Show HN pre-submit checklist — secrets, paste SSOT, smoke, forbidden copy."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/universal_root_show_hn_launch_checklist_v1_latest.json"
PASTE = {
    "title": ROOT / "reports/human_paste/universal_root_show_hn_title.txt",
    "body": ROOT / "reports/human_paste/universal_root_show_hn_body.md",
    "first_comment": ROOT / "reports/human_paste/universal_root_show_hn_first_comment.md",
}
FORBIDDEN = [
    "gpt killer",
    "gpt-killer",
    "global hallucination rate",
    "zero hallucination",
    "47.5%",
    "99.53% compression",
]
REPO_URL = "https://github.com/mkmlab-v2/mkm-universal-root"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(script: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()[-600:]


def _scan_forbidden(text: str) -> list[str]:
    low = text.lower()
    hits: list[str] = []
    for phrase in FORBIDDEN:
        if phrase not in low:
            continue
        if phrase == "47.5%" and ("not in this export" in low or "compression kpi" in low):
            continue
        if phrase == "global hallucination rate" and "not a global" in low:
            continue
        hits.append(phrase)
    return hits


def main() -> int:
    checks: dict[str, Any] = {}
    violations: list[str] = []

    for name, path in PASTE.items():
        text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
        bad = _scan_forbidden(text)
        checks[f"paste_{name}"] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "exists": path.is_file(),
            "chars": len(text),
            "forbidden_hits": bad,
        }
        if not path.is_file():
            violations.append(f"missing_paste_{name}")
        if bad:
            violations.append(f"forbidden_in_{name}")

    title = PASTE["title"].read_text(encoding="utf-8-sig") if PASTE["title"].is_file() else ""
    if title and not title.strip().lower().startswith("show hn:"):
        violations.append("title_must_start_with_show_hn")

    code, tail = _run("check_mkm_secret_patterns_v1.py")
    checks["secret_scan"] = {"exit_code": code, "ok": code == 0, "tail": tail}
    if code != 0:
        violations.append("secret_scan_failed")

    code, tail = _run("check_hardcoded_workspace_paths_v1.py", "--scope", "oss", "--strict")
    checks["oss_path_audit"] = {"exit_code": code, "ok": code == 0, "tail": tail}
    if code != 0:
        violations.append("oss_path_audit_failed")

    code, tail = _run("run_universal_root_oss_cursor_smoke_v1.py")
    checks["smoke"] = {"exit_code": code, "ok": code == 0, "tail": tail}
    if code != 0:
        violations.append("smoke_failed")

    smoke_path = ROOT / "reports/universal_root_oss_cursor_smoke_v1_latest.json"
    smoke_doc = json.loads(smoke_path.read_text(encoding="utf-8-sig")) if smoke_path.is_file() else {}
    checks["smoke_metrics"] = smoke_doc.get("metrics")

    code, _ = _run("build_mkm_universal_root_public_export_bundle_v1.py", "--verify-only")
    checks["export_verify"] = {"exit_code": code, "ok": code == 0}
    if code != 0:
        violations.append("export_verify_failed")

    doc = {
        "schema": "universal_root_show_hn_launch_checklist_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "repo_url": REPO_URL,
        "submit_url": "https://news.ycombinator.com/submit",
        "account_handle": "moksorinw",
        "checks": checks,
        "violations": violations,
        "ok": not violations,
        "semi_auto": "powershell -File scripts/Invoke-UniversalRootShowHnSemiAuto_v1.ps1",
        "reproduce": "py scripts/build_universal_root_show_hn_launch_checklist_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "violations": violations, "out": str(OUT).replace(chr(92), "/")}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
