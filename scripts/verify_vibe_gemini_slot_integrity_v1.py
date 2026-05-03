#!/usr/bin/env python3
"""Verify Athena raw markdown outputs are not legacy bootstrap/stub artifacts.

This is intentionally lightweight string scanning (Fact-Lock friendly): it flags known
research_stub/bootstrap markers and optionally requires the Gemini runtime header used by
`scripts/generate_gemini_athena_slots_v1.py`.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_RUNS = ART / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"
DEFAULT_RAW_DIR = ART / "vibe_runs_raw" / "athena_raw_outputs"
OUT_JSON = ART / "vibe_runs_raw" / "vibe_gemini_slot_integrity_latest.json"
OUT_MD = ART / "vibe_runs_raw" / "vibe_gemini_slot_integrity_latest.md"


STUB_MARKERS = (
    "research_stub_evidence_v1",
    "bootstrap_replacement",
    "legacy_bootstrap",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def expected_filename(prompt_id: str, run_index: int) -> str:
    return f"{prompt_id}_run_{run_index:02d}.md"


_RE_STUB_LINE = re.compile(r"(?im)^\s*Stub:\s+.+$")


def has_gemini_runtime_header(text: str) -> bool:
    t = text
    if re.search(r"(?im)^\s*runtime:\s+.*gemini", t):
        return True
    # Accept alternate phrasing if models drift slightly, but still require "Gemini".
    if "gemini" in t.lower() and ("runtime" in t.lower() or "persona" in t.lower()):
        return True
    return False


def detect_stub_reasons(text: str) -> list[str]:
    reasons: list[str] = []
    upper = text.upper()
    for m in STUB_MARKERS:
        if m in text:
            reasons.append(f"marker:{m}")
    if _RE_STUB_LINE.search(text):
        reasons.append("line:Stub:")
    # Slot template placeholder means generation never replaced the decision token union.
    if "FINAL ACTION: HOLD|REDUCE|WATCH" in upper:
        reasons.append("template:FINAL_ACTION_UNION")
    return sorted(set(reasons))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-jsonl", type=str, default=str(DEFAULT_RUNS))
    parser.add_argument("--raw-dir", type=str, default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--require-runtime-header", action="store_true")
    parser.add_argument("--fail-on-extra-files", action="store_true")
    parser.add_argument("--out-json", type=str, default=str(OUT_JSON))
    parser.add_argument("--out-md", type=str, default=str(OUT_MD))
    args = parser.parse_args()

    runs_path = Path(args.runs_jsonl)
    raw_dir = Path(args.raw_dir)
    rows = read_jsonl(runs_path)

    expected_files: list[str] = []
    for row in rows:
        pid = str(row.get("prompt_id"))
        rid = int(row.get("run_index"))
        expected_files.append(expected_filename(pid, rid))

    issues: dict[str, Any] = {
        "missing_files": [],
        "stub_like_files": [],
        "missing_runtime_header": [],
        "extra_files": [],
        "per_file": {},
    }

    existing = sorted(raw_dir.glob("prompt_*_run_*.md"))
    existing_set = {p.name for p in existing}
    expected_set = set(expected_files)

    if args.fail_on_extra_files:
        extras = sorted(existing_set - expected_set)
        issues["extra_files"] = extras

    exit_code = 0

    for fname in expected_files:
        path = raw_dir / fname
        if not path.is_file():
            issues["missing_files"].append(fname)
            exit_code = 2
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        stub_reasons = detect_stub_reasons(text)
        if stub_reasons:
            issues["stub_like_files"].append({"file": fname, "reasons": stub_reasons})
            issues["per_file"][fname] = {"stub_like": True, "reasons": stub_reasons}
            exit_code = 2
        else:
            issues["per_file"][fname] = {"stub_like": False, "reasons": []}

        if args.require_runtime_header and (not has_gemini_runtime_header(text)):
            issues["missing_runtime_header"].append(fname)
            exit_code = 2

    if args.fail_on_extra_files and issues["extra_files"]:
        exit_code = 2

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok = exit_code == 0
    report = {
        "schema": "vibe_gemini_slot_integrity_v1",
        "generated_at_utc": now,
        "scope": "research_only",
        "runs_file": str(runs_path).replace("\\", "/"),
        "raw_dir": str(raw_dir).replace("\\", "/"),
        "require_runtime_header": bool(args.require_runtime_header),
        "fail_on_extra_files": bool(args.fail_on_extra_files),
        "expected_files": len(expected_files),
        "status": "ok" if ok else "fail",
        "issues": issues,
    }

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Vibe Gemini Slot Integrity (Latest)",
        "",
        f"- Generated (UTC): {now}",
        f"- Runs file: `{report['runs_file']}`",
        f"- Raw dir: `{report['raw_dir']}`",
        f"- Expected files: {report['expected_files']}",
        f"- Require runtime header: {str(args.require_runtime_header).lower()}",
        f"- Fail on extra files: {str(args.fail_on_extra_files).lower()}",
        f"- Status: {report['status']}",
        "",
    ]
    if issues["missing_files"]:
        md_lines += ["## Missing files", *[f"- {x}" for x in issues["missing_files"]], ""]
    if issues["stub_like_files"]:
        md_lines += ["## Stub-like outputs", ""]
        for item in issues["stub_like_files"]:
            md_lines.append(f"- `{item['file']}`: {', '.join(item['reasons'])}")
        md_lines.append("")
    if issues["missing_runtime_header"]:
        md_lines += ["## Missing Gemini runtime header", *[f"- {x}" for x in issues["missing_runtime_header"]], ""]
    if issues["extra_files"]:
        md_lines += ["## Extra unexpected files", *[f"- {x}" for x in issues["extra_files"]], ""]
    out_md.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"written: {out_json}")
    print(f"written: {out_md}")
    print(f"status: {report['status']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
