#!/usr/bin/env python3
"""Prune rotated symbol C delta alert logs by day retention."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_RETENTION_TEMPLATE = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_delta_log_retention_template.json"
)
DATE_RE = re.compile(r"^delta_alert_log_(\d{8})\.jsonl$")


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _parse_yyyymmdd(tag: str) -> datetime | None:
    try:
        return datetime.strptime(tag, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_keep_days(template_path: Path, fallback: int) -> int:
    if not template_path.is_file():
        return fallback
    try:
        data = json.loads(template_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback
    raw = data.get("keep_latest_days", fallback) if isinstance(data, dict) else fallback
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return fallback


def main() -> int:
    ap = argparse.ArgumentParser(description="Prune rotated delta alert logs by retention days")
    ap.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    ap.add_argument("--keep-latest-days", type=int, default=30)
    ap.add_argument("--retention-template", default=str(DEFAULT_RETENTION_TEMPLATE))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    report_dir = _abs(args.report_dir)
    keep_days = _load_keep_days(_abs(args.retention_template), max(1, int(args.keep_latest_days)))
    if not report_dir.is_dir():
        print(f"OK: report dir missing, nothing to prune ({report_dir})")
        return 0

    now = datetime.now(timezone.utc)
    pruned = 0
    kept = 0
    for p in report_dir.iterdir():
        if not p.is_file():
            continue
        m = DATE_RE.match(p.name)
        if not m:
            continue
        dt = _parse_yyyymmdd(m.group(1))
        if dt is None:
            continue
        age_days = (now - dt).days
        if age_days >= keep_days:
            if args.dry_run:
                print(f"DRY-RUN PRUNE: {p}")
            else:
                p.unlink(missing_ok=True)
                print(f"PRUNE: {p}")
            pruned += 1
        else:
            kept += 1

    print("OK: delta alert log prune completed")
    print(f"report_dir={report_dir}")
    print(f"kept={kept} pruned={pruned} keep_latest_days={keep_days} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
