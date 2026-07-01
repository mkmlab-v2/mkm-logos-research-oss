#!/usr/bin/env python3
"""Lightweight secret-pattern scan for solo OSS pre-push (no gitleaks required).

Scans git-tracked paths (or --staged only) for high-confidence secret material.

  py scripts/check_mkm_secret_patterns_v1.py
  py scripts/check_mkm_secret_patterns_v1.py --staged
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/mkm_secret_pattern_scan_v1_latest.json"

SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".wasm", ".pyc",
}
SKIP_PARTS = ("/.vendor/", "/vendor/", "/node_modules/", "/.git/")

ALLOW_PATH_RE = re.compile(
    r"(?i)(\.env\.example|template\.(md|json|txt)$|_TEMPLATE\.|"
    r"PUBLIC_FACING_SECURITY|check_mkm_secret_patterns_v1\.py|\.gitleaks\.toml$)"
)

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{36,}")),
    ("openai_sk", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "assignment_secret",
        re.compile(
            r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)"
            r"\s*=\s*['\"]?([^\s'\"#]{24,})"
        ),
    ),
]

PLACEHOLDER_RE = re.compile(
    r"(?i)(example|placeholder|changeme|redacted|your_|insert|<your|xxx+|000000|"
    r"not.?set|dummy|fake|sample|test.?key)"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_paths(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    if not staged:
        cmd = ["git", "ls-files"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git path listing failed")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _should_skip(rel: str) -> bool:
    if ALLOW_PATH_RE.search(rel):
        return True
    path = rel.replace("\\", "/")
    if any(part in path for part in SKIP_PARTS):
        return True
    suffix = Path(rel).suffix.lower()
    return suffix in SKIP_SUFFIXES


def _line_uses_env_ref(line: str) -> bool:
    return bool(re.search(r"(?i)(process\.env|os\.environ|getenv\s*\(|ENV\[)", line))


def _scan_file(rel: str) -> list[dict[str, str]]:
    path = ROOT / rel
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    hits: list[dict[str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _line_uses_env_ref(line):
            continue
        for name, pattern in PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            sample = m.group(1) if m.lastindex else m.group(0)
            if PLACEHOLDER_RE.search(sample) or PLACEHOLDER_RE.search(line):
                continue
            hits.append({"path": rel, "line": str(line_no), "rule": name, "preview": stripped[:80]})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--staged", action="store_true", help="Scan git index (pre-commit) only")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    paths = _git_paths(staged=args.staged)
    findings: list[dict[str, str]] = []
    scanned = 0
    for rel in paths:
        if _should_skip(rel):
            continue
        scanned += 1
        findings.extend(_scan_file(rel))

    doc = {
        "schema": "mkm_secret_pattern_scan_v1",
        "generated_at_utc": _utc(),
        "ok": not findings,
        "mode": "staged" if args.staged else "tracked",
        "scanned_files": scanned,
        "finding_count": len(findings),
        "findings": findings[:50],
        "reproduce": "py scripts/check_mkm_secret_patterns_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if findings:
        for f in findings[:10]:
            print(f"FAIL: {f['path']}:{f['line']} [{f['rule']}]", file=sys.stderr)
        if len(findings) > 10:
            print(f"... and {len(findings) - 10} more", file=sys.stderr)
        print(f"artifact: {args.out}", file=sys.stderr)
        return 1
    print(f"OK: secret pattern scan ({scanned} files) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
