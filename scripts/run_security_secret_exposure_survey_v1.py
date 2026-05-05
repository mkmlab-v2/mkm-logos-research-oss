#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "security_secret_exposure_survey_latest.json"

DEFAULT_SECRET_ENV_KEYS = [
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "FRED_API_KEY",
    "NEWSAPI_API_KEY",
    "OPS_ALARM_WEBHOOK_URL",
    "ATHENA_ECC_AUDIT_WEBHOOK_URL",
]

TEXT_FILE_EXT_ALLOWLIST = {
    ".py",
    ".ps1",
    ".sh",
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".env",
    ".example",
    ".toml",
    ".ini",
    ".cfg",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".cursor",
    "tmp",
    "temp",
}

PATTERN_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("github_pat", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "generic_api_key_assignment",
        re.compile(r"(?i)\b(api[-_ ]?key|secret|token)\b\s*[:=]\s*['\"][^'\"$]{10,}['\"]"),
    ),
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE_ROOT))
    except ValueError:
        return str(path)


def _iter_text_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if len(files) >= max_files:
            break
        if not p.is_file():
            continue
        if any(part in DEFAULT_EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in TEXT_FILE_EXT_ALLOWLIST:
            if p.name not in {".env", ".env.example", ".gitignore", ".cursorrules"}:
                continue
        if p.name.startswith("security_secret_exposure_survey_"):
            continue
        files.append(p)
    return files


def _read_text(path: Path, max_bytes_per_file: int) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if len(raw) > max_bytes_per_file:
        raw = raw[:max_bytes_per_file]
    return raw.decode("utf-8", errors="ignore")


def _hash_label(secret: str) -> str:
    h = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return f"sha256:{h[:16]}"


def run_survey(
    *,
    roots: list[Path],
    secret_env_keys: list[str],
    max_files: int,
    max_bytes_per_file: int,
) -> dict[str, Any]:
    findings_exact: list[dict[str, Any]] = []
    findings_pattern: list[dict[str, Any]] = []
    scanned_file_count = 0
    scanned_roots: list[str] = []

    secret_values: dict[str, str] = {}
    for key in secret_env_keys:
        val = (os.environ.get(key) or "").strip()
        if val and len(val) >= 8:
            secret_values[key] = val

    for root in roots:
        if not root.exists():
            continue
        scanned_roots.append(_safe_rel(root))
        for file_path in _iter_text_files(root, max_files=max_files):
            scanned_file_count += 1
            text = _read_text(file_path, max_bytes_per_file=max_bytes_per_file)
            if not text:
                continue

            for env_key, secret in secret_values.items():
                if secret in text:
                    findings_exact.append(
                        {
                            "type": "exact_secret_value_match",
                            "env_key": env_key,
                            "value_hash_label": _hash_label(secret),
                            "path": _safe_rel(file_path),
                        }
                    )

            for rule_name, rule in PATTERN_RULES:
                m = rule.search(text)
                if m:
                    findings_pattern.append(
                        {
                            "type": "suspicious_secret_pattern",
                            "rule": rule_name,
                            "path": _safe_rel(file_path),
                            "sample": m.group(0)[:120],
                        }
                    )

    severity = "ok"
    if findings_exact:
        severity = "critical"
    elif findings_pattern:
        severity = "warning"

    return {
        "schema": "security_secret_exposure_survey_v1",
        "ts_utc": _now_utc(),
        "workspace_root": str(WORKSPACE_ROOT),
        "scanned_roots": scanned_roots,
        "scanned_file_count": scanned_file_count,
        "configured_secret_env_keys": secret_env_keys,
        "active_secret_env_keys_count": len(secret_values),
        "findings": {
            "exact_matches": findings_exact,
            "pattern_matches": findings_pattern,
        },
        "summary": {
            "exact_match_count": len(findings_exact),
            "pattern_match_count": len(findings_pattern),
            "severity": severity,
        },
        "boundary_ack": True,
        "note": "Day1 secret exposure survey (value-safe, no plaintext secret output).",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run Day1 secret exposure path survey.")
    ap.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--roots",
        default="scripts,projects,docs/final,reports,.env.example,.gitignore",
        help="Comma-separated paths relative to workspace root to scan.",
    )
    ap.add_argument(
        "--secret-env-keys",
        default=",".join(DEFAULT_SECRET_ENV_KEYS),
        help="Comma-separated env keys to probe for exact value leakage.",
    )
    ap.add_argument("--max-files", type=int, default=2500)
    ap.add_argument("--max-bytes-per-file", type=int, default=1_500_000)
    ap.add_argument("--strict-exit", action="store_true")
    ap.add_argument("--webhook-env", default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument(
        "--dispatch-on",
        default="critical",
        choices=("off", "warning", "critical"),
        help="Webhook dispatch threshold: off | warning | critical",
    )
    ap.add_argument("--webhook-timeout-sec", type=int, default=10)
    ap.add_argument("--webhook-retries", type=int, default=2)
    ap.add_argument("--webhook-retry-backoff-sec", type=float, default=1.0)
    ap.add_argument("--webhook-dry-run", action="store_true")
    return ap.parse_args(argv)


def _build_alert_payload(report: dict[str, Any]) -> dict[str, Any]:
    exact = report.get("findings", {}).get("exact_matches", [])
    pattern = report.get("findings", {}).get("pattern_matches", [])
    return {
        "schema": "security_secret_exposure_alert_v1",
        "ts_utc": report.get("ts_utc"),
        "severity": report.get("summary", {}).get("severity"),
        "exact_match_count": report.get("summary", {}).get("exact_match_count", 0),
        "pattern_match_count": report.get("summary", {}).get("pattern_match_count", 0),
        "top_exact_paths": [x.get("path") for x in exact[:5] if isinstance(x, dict)],
        "top_pattern_paths": [x.get("path") for x in pattern[:5] if isinstance(x, dict)],
        "scanned_file_count": report.get("scanned_file_count", 0),
    }


def _dispatch_webhook(
    *,
    url: str,
    payload: dict[str, Any],
    timeout_sec: int,
    retries: int,
    backoff_sec: float,
    dry_run: bool,
) -> dict[str, Any]:
    if not url:
        return {"status": "skipped", "reason": "webhook_not_configured"}
    if dry_run:
        return {"status": "dry_run"}

    tries = max(1, int(retries))
    timeout = max(1, int(timeout_sec))
    backoff = max(0.0, float(backoff_sec))
    last_err = ""
    for idx in range(tries):
        req = request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                return {"status": "sent", "http_status": int(resp.getcode()), "attempt": idx + 1}
        except (error.URLError, TimeoutError, OSError) as exc:
            last_err = str(exc)
            if idx < tries - 1 and backoff > 0:
                time.sleep(backoff)
    return {"status": "failed", "error": last_err, "attempts": tries}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots: list[Path] = []
    for raw in str(args.roots).split(","):
        item = raw.strip()
        if not item:
            continue
        p = Path(item)
        if not p.is_absolute():
            p = args.workspace_root / p
        roots.append(p)
    keys = [k.strip() for k in str(args.secret_env_keys).split(",") if k.strip()]
    report = run_survey(
        roots=roots,
        secret_env_keys=keys,
        max_files=max(1, int(args.max_files)),
        max_bytes_per_file=max(1024, int(args.max_bytes_per_file)),
    )
    severity = str(report.get("summary", {}).get("severity", "ok"))
    should_dispatch = False
    if args.dispatch_on == "warning" and severity in {"warning", "critical"}:
        should_dispatch = True
    elif args.dispatch_on == "critical" and severity == "critical":
        should_dispatch = True

    report["dispatch"] = {"status": "skipped", "reason": "threshold_not_met"}
    if should_dispatch:
        webhook_url = (os.environ.get(str(args.webhook_env)) or "").strip()
        payload = _build_alert_payload(report)
        report["dispatch"] = _dispatch_webhook(
            url=webhook_url,
            payload=payload,
            timeout_sec=int(args.webhook_timeout_sec),
            retries=int(args.webhook_retries),
            backoff_sec=float(args.webhook_retry_backoff_sec),
            dry_run=bool(args.webhook_dry_run),
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
                "severity": report["summary"]["severity"],
                "exact_match_count": report["summary"]["exact_match_count"],
                "pattern_match_count": report["summary"]["pattern_match_count"],
                "dispatch_status": report.get("dispatch", {}).get("status"),
            },
            ensure_ascii=False,
        )
    )

    if args.strict_exit and (
        int(report["summary"]["exact_match_count"]) > 0 or int(report["summary"]["pattern_match_count"]) > 0
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
