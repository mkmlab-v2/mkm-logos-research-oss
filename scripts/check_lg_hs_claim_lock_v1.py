#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


RISK_PATTERNS: list[tuple[str, str]] = [
    ("absolute_claim", r"(절대|완벽|100%\s*보장|리스크\s*제로|무조건|원천봉쇄)"),
    ("hype_claim", r"(기적|마법|무한(한)?\s*확장성|한\s*치의\s*오차\s*없이|압도)"),
    ("spec_overclaim", r"(0\.008초|1,600개\s*조합\s*스윕)"),
    ("expansion_overclaim", r"(드론|자율주행|스마트안경).*(즉시|확정|바로)"),
]

NEGATION_HINT = re.compile(
    r"(금지|하지\s*말|과장\s*금지|단정\s*금지|말하면\s*안|금지어|절대\s*말해야|절대\s*암기)",
    flags=re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LG HS claim lock checker (anti-overclaim guard).")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--glob", default="*lg_hs*.md")
    p.add_argument(
        "--mode",
        choices=("strict", "presentation"),
        default="presentation",
        help="strict: include all lines, presentation: skip prohibition/example sections.",
    )
    p.add_argument("--output-json", default="reports/lg_hs_claim_lock_latest.json")
    p.add_argument("--output-md", default="reports/lg_hs_claim_lock_latest.md")
    return p.parse_args()


def _should_skip_line(line: str) -> bool:
    return bool(NEGATION_HINT.search(line))


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    artifacts = root / "docs" / "final" / "artifacts"
    files = sorted(artifacts.glob(args.glob))

    findings: list[dict[str, str | int]] = []
    for f in files:
        lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        for idx, line in enumerate(lines, start=1):
            if args.mode == "presentation" and _should_skip_line(line):
                continue
            for category, pattern in RISK_PATTERNS:
                if re.search(pattern, line):
                    findings.append(
                        {
                            "file": str(f.relative_to(root)).replace("\\", "/"),
                            "line": idx,
                            "category": category,
                            "pattern": pattern,
                            "text": line.strip(),
                        }
                    )

    payload = {
        "schema": "lg_hs_claim_lock_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_glob": args.glob,
        "mode": args.mode,
        "file_count": len(files),
        "finding_count": len(findings),
        "status": "PASS" if not findings else "WARN",
        "findings": findings,
    }

    output_json = root / args.output_json
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# LG HS Claim Lock Report",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- file_count: `{payload['file_count']}`",
        f"- mode: `{payload['mode']}`",
        f"- finding_count: `{payload['finding_count']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Findings",
    ]
    if findings:
        for item in findings:
            md_lines.append(
                f"- `{item['file']}` line `{item['line']}` [{item['category']}]: `{item['text']}`"
            )
    else:
        md_lines.append("- none")

    output_md = root / args.output_md
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"lg_hs_claim_lock_written={output_json.as_posix()}")
    print(f"lg_hs_claim_lock_status={payload['status']} findings={payload['finding_count']}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
