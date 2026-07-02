#!/usr/bin/env python3
"""Static + subprocess checks for Logos Ask invariants v1."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/fixtures/logos_ask_invariants_v1.json"
ROUTE = ROOT / "projects/no1kmedi/src/app/api/logos-research/query/route.ts"
STUDIO = ROOT / "projects/no1kmedi/src/lib/logosResearchStudioV1.ts"
DISPLAY_SMOKE = ROOT / "projects/no1kmedi/scripts/smoke-logos-ask-display-invariants-v1.ts"


def check_inv01_inquiry_no_job_fallback() -> tuple[bool, str]:
    text = ROUTE.read_text(encoding="utf-8")
    if "LOGOS_GRAPH_STUDIO_DEFAULT_PRESET" not in text:
        return False, "missing LOGOS_GRAPH_STUDIO_DEFAULT_PRESET reference"
    for match in re.finditer("LOGOS_GRAPH_STUDIO_DEFAULT_PRESET", text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end < 0:
            line_end = len(text)
        line = text[line_start:line_end]
        if "import" in line:
            continue
        ctx = text[max(0, match.start() - 320) : match.end() + 120]
        if "textMvpMode" not in ctx:
            return False, f"job default preset outside textMvpMode: {line.strip()[:80]}"
    return True, "inquiry_report_v1 has no job fallback; text_mvp only"


def check_inv02_hub_stub_no_synthesis() -> tuple[bool, str]:
    text = STUDIO.read_text(encoding="utf-8")
    needles = [
        "topic_mismatch_guard",
        "applyQueryTopicMismatchGuardAsync",
        "includes(\"topic_mismatch_guard\")",
    ]
    missing = [n for n in needles if n not in text]
    if missing:
        return False, f"studio missing guards: {missing}"
    if "topicMismatch" not in text and "topic_mismatch" not in text:
        return False, "topic mismatch skip path not found"
    return True, "topic_mismatch_guard wired in studio pipeline"


def check_inv03_display_strip() -> tuple[bool, str]:
    if not DISPLAY_SMOKE.is_file():
        return False, f"missing {DISPLAY_SMOKE.name}"
    proc = subprocess.run(
        ["npx", "tsx", str(DISPLAY_SMOKE)],
        cwd=ROOT / "projects/no1kmedi",
        capture_output=True,
        text=True,
        shell=True,
    )
    if proc.returncode != 0:
        return False, (proc.stdout + proc.stderr).strip()[:400]
    return True, "display strip smoke exit 0"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    checks = [
        ("INV-01", "inquiry_no_job_fallback", check_inv01_inquiry_no_job_fallback),
        ("INV-02", "hub_stub_no_synthesis", check_inv02_hub_stub_no_synthesis),
        ("INV-03", "public_ui_no_research_tags", check_inv03_display_strip),
    ]
    rows = []
    ok_all = True
    for inv_id, code, fn in checks:
        ok, detail = fn()
        rows.append({"id": inv_id, "code": code, "ok": ok, "detail": detail})
        ok_all = ok_all and ok

    report = {
        "schema": "logos_ask_invariants_check_v1",
        "fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "ok": ok_all,
        "rows": rows,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok_all, "passed": sum(1 for r in rows if r["ok"]), "total": len(rows)}, ensure_ascii=False))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
