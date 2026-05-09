#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "ip_fortress_scrubber_latest.json"

DEFAULT_TARGETS = [
    "projects/no1kmedi",
    "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp",
    "docs/final/artifacts/showroom_public_bundle_v1.json",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".cursor",
    "tmp",
    "temp",
}

EXCLUDED_FILE_NAMES = {
    ".env.example",
}

TEXT_EXT_ALLOW = {
    ".py",
    ".ps1",
    ".sh",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
}

# Keep this list conservative to avoid false positives while still blocking likely leaks.
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("discord_webhook_url", re.compile(r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_\-]+", re.I)),
    ("generic_webhook_url", re.compile(r"https?://[^\s\"']*webhook[^\s\"']*", re.I)),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("binance_key_assignment", re.compile(r"(?i)\b(BINANCE_API_KEY|BINANCE_API_SECRET)\b\s*[:=]\s*['\"][^'\"\n]{8,}['\"]")),
    ("db_connection_string", re.compile(r"(?i)\b(postgres|mysql|mongodb)(?:\+srv)?:\/\/[^ \n\"']+")),
    ("internal_private_ip", re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b")),
    ("cursor_local_windows_path", re.compile(r"C:\\\\Users\\\\[^\\\s]+\\\\", re.I)),
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _iter_files(base: Path, max_files: int) -> list[Path]:
    out: list[Path] = []
    if base.is_file():
        return [base]
    for p in base.rglob("*"):
        if len(out) >= max_files:
            break
        if not p.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in p.parts):
            continue
        if p.name in EXCLUDED_FILE_NAMES:
            continue
        if p.suffix.lower() == ".example":
            continue
        if p.suffix.lower() not in TEXT_EXT_ALLOW and p.name not in {".env", ".env.example", ".gitignore"}:
            continue
        out.append(p)
    return out


def _read_text(path: Path, max_bytes: int) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="ignore")


def run_scrub(*, targets: list[Path], max_files: int, max_bytes_per_file: int) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned_files = 0
    scanned_targets: list[str] = []

    for t in targets:
        if not t.exists():
            continue
        scanned_targets.append(_safe_rel(t))
        for fp in _iter_files(t, max_files=max_files):
            scanned_files += 1
            text = _read_text(fp, max_bytes=max_bytes_per_file)
            if not text:
                continue
            for rule_name, rule in RULES:
                m = rule.search(text)
                if not m:
                    continue
                findings.append(
                    {
                        "rule": rule_name,
                        "path": _safe_rel(fp),
                        "sample": m.group(0)[:160],
                    }
                )

    severity = "PASS" if len(findings) == 0 else "BLOCK"
    return {
        "schema": "ip_fortress_scrubber_v1",
        "generated_at_utc": _now_utc(),
        "summary": {
            "status": severity,
            "finding_count": len(findings),
            "scanned_file_count": scanned_files,
        },
        "scanned_targets": scanned_targets,
        "findings": findings[:200],
        "ruleset": [name for name, _ in RULES],
        "note": "Public snapshot sanitizer for deploy-time gating.",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="IP fortress public snapshot scrubber")
    ap.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    ap.add_argument("--targets", default=",".join(DEFAULT_TARGETS))
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-files", type=int, default=2000)
    ap.add_argument("--max-bytes-per-file", type=int, default=1_500_000)
    ap.add_argument("--strict-exit", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets: list[Path] = []
    for raw in str(args.targets).split(","):
        item = raw.strip()
        if not item:
            continue
        p = Path(item)
        if not p.is_absolute():
            p = args.workspace_root / p
        targets.append(p)

    report = run_scrub(
        targets=targets,
        max_files=max(1, int(args.max_files)),
        max_bytes_per_file=max(2048, int(args.max_bytes_per_file)),
    )

    out_path = args.out
    if not out_path.is_absolute():
        out_path = args.workspace_root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "out": _safe_rel(out_path),
                "status": report["summary"]["status"],
                "finding_count": report["summary"]["finding_count"],
                "scanned_file_count": report["summary"]["scanned_file_count"],
            },
            ensure_ascii=False,
        )
    )

    if args.strict_exit and report["summary"]["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

