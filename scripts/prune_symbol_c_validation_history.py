#!/usr/bin/env python3
"""Prune old symbol C validation history directories."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HISTORY_ROOT = ROOT / "reports" / "constitution" / "btrack_pilot" / "history" / "symbol_c_validation"
DEFAULT_RETENTION_TEMPLATE = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_history_retention_template_prod.json"
)


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_keep_latest(template_path: Path, fallback: int) -> int:
    if not template_path.is_file():
        return fallback
    try:
        data = json.loads(template_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return fallback
    raw = data.get("keep_latest_runs", fallback) if isinstance(data, dict) else fallback
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return fallback


def main() -> int:
    ap = argparse.ArgumentParser(description="Prune old symbol C validation history directories")
    ap.add_argument("--history-root", default=str(DEFAULT_HISTORY_ROOT))
    ap.add_argument("--keep-latest", type=int, default=20)
    ap.add_argument("--retention-template", default=str(DEFAULT_RETENTION_TEMPLATE))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    history_root = _abs(args.history_root)
    keep_latest = _load_keep_latest(_abs(args.retention_template), max(1, int(args.keep_latest)))
    if not history_root.is_dir():
        print(f"OK: history root missing, nothing to prune ({history_root})")
        return 0

    dirs = [p for p in history_root.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.name, reverse=True)

    kept = dirs[:keep_latest]
    pruned = dirs[keep_latest:]
    for d in pruned:
        if args.dry_run:
            print(f"DRY-RUN PRUNE: {d}")
        else:
            shutil.rmtree(d, ignore_errors=True)
            print(f"PRUNE: {d}")

    print("OK: symbol C validation history prune completed")
    print(f"history_root={history_root}")
    print(f"kept={len(kept)} pruned={len(pruned)} keep_latest={keep_latest} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
