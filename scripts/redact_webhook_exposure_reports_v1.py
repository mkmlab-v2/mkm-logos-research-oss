#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = WORKSPACE_ROOT / "projects" / "mkm" / "mkm-life" / "reports"
REDACTED = "[REDACTED_WEBHOOK_URL]"


def _iter_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*.json") if p.is_file()]


def _replace_webhook_values(content: str, exact_values: list[str]) -> tuple[str, int]:
    total = 0
    text = content

    for value in exact_values:
        if not value:
            continue
        c = text.count(value)
        if c > 0:
            text = text.replace(value, REDACTED)
            total += c

    # Also redact literal webhook URLs in known JSON fields.
    patterns = [
        re.compile(r'("webhook_target"\s*:\s*")([^"]+)(")'),
        re.compile(r'("webhook_url"\s*:\s*")([^"]+)(")'),
    ]
    for pat in patterns:
        text, c = pat.subn(rf"\1{REDACTED}\3", text)
        total += c
    return text, total


def run(root: Path) -> dict[str, Any]:
    env_candidates = [
        (os.environ.get("OPS_ALARM_WEBHOOK_URL") or "").strip(),
        (os.environ.get("DAILY_OPS_ALERT_WEBHOOK_URL") or "").strip(),
        (os.environ.get("ATHENA_ECC_AUDIT_WEBHOOK_URL") or "").strip(),
    ]
    env_values = [v for v in env_candidates if v]

    changed_files: list[dict[str, Any]] = []
    scanned = 0
    replaced_total = 0
    for path in _iter_json_files(root):
        scanned += 1
        try:
            before = path.read_text(encoding="utf-8")
        except OSError:
            continue
        after, replaced = _replace_webhook_values(before, env_values)
        if replaced <= 0 or after == before:
            continue
        path.write_text(after, encoding="utf-8")
        changed_files.append(
            {
                "path": str(path.relative_to(WORKSPACE_ROOT)),
                "replacements": int(replaced),
            }
        )
        replaced_total += int(replaced)

    return {
        "schema": "redact_webhook_exposure_reports_v1",
        "root": str(root),
        "scanned_file_count": scanned,
        "changed_file_count": len(changed_files),
        "replacements_total": replaced_total,
        "changed_files": changed_files,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Redact webhook exposure from report JSON files.")
    ap.add_argument("--root", type=Path, default=DEFAULT_REPORT_DIR)
    ap.add_argument("--out", type=Path, default=WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "webhook_redaction_report_latest.json")
    args = ap.parse_args(argv)
    root = args.root if args.root.is_absolute() else WORKSPACE_ROOT / args.root
    result = run(root)
    out = args.out if args.out.is_absolute() else WORKSPACE_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed_file_count": result["changed_file_count"], "replacements_total": result["replacements_total"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
