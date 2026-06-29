#!/usr/bin/env python3
"""Remove example/HYPO rows from commander interest signal JSONL (archive optional)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from commander_interest_benchmark_v1_lib import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_LOG,
    is_excluded_signal,
    load_config,
    resolve_path,
)

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "commander_interest_signal_log_prune_latest.json"


def prune_log(
    *,
    log_path: Path,
    config_path: Path,
    archive_path: Path | None,
    dry_run: bool,
) -> dict[str, Any]:
    config = load_config(config_path)
    log_path = resolve_path(log_path)
    if not log_path.is_file():
        raise FileNotFoundError(f"Missing log: {log_path}")

    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if is_excluded_signal(row, config):
            removed.append(row)
        else:
            kept.append(row)

    if not dry_run:
        if archive_path and removed:
            archive = resolve_path(archive_path)
            archive.parent.mkdir(parents=True, exist_ok=True)
            with archive.open("a", encoding="utf-8") as fh:
                for row in removed:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        log_path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept),
            encoding="utf-8",
        )

    return {
        "schema": "commander_interest_signal_log_prune_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dry_run": dry_run,
        "log_path": str(log_path.resolve()),
        "kept_count": len(kept),
        "removed_count": len(removed),
        "removed_sample_titles": [str(r.get("title") or "")[:80] for r in removed[:5]],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument(
        "--archive-jsonl",
        type=Path,
        default=ROOT / "reports" / "commander_interest_signal_log_v1_removed_archive.jsonl",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    payload = prune_log(
        log_path=args.log_jsonl,
        config_path=args.config_json,
        archive_path=None if args.no_archive else args.archive_jsonl,
        dry_run=args.dry_run,
    )
    out = resolve_path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out), **payload}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
