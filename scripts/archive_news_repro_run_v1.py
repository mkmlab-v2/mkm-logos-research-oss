#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "external_runner_manifest.json",
    "raw_benchmark.log",
    "independent_result_digest.json",
    "signed_repro_statement.txt",
]


def _read_json(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    raise ValueError(f"Failed to parse JSON: {path}")


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    return value.strip("-") or "unknown-runner"


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive current news repro dropzone into immutable run folder.")
    parser.add_argument("--dropzone", default="reports/news_repro/latest", help="Source dropzone directory")
    parser.add_argument(
        "--archive-root",
        default="reports/news_repro/runs",
        help="Archive root directory (new run folder will be created inside)",
    )
    parser.add_argument("--runner-id", default="", help="Override runner_id (default: digest/manifest value)")
    parser.add_argument("--label", default="", help="Optional label suffix for run folder")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    dropzone = (root / args.dropzone).resolve()
    archive_root = (root / args.archive_root).resolve()

    missing = [name for name in REQUIRED_FILES if not (dropzone / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files in dropzone: {missing}")

    digest = _read_json(dropzone / "independent_result_digest.json")
    manifest = _read_json(dropzone / "external_runner_manifest.json")
    runner_id = args.runner_id.strip() or str(digest.get("runner_id") or manifest.get("runner_id") or "").strip()
    runner_slug = _slug(runner_id or "unknown-runner")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label_suffix = f"_{_slug(args.label)}" if args.label.strip() else ""
    run_dir = archive_root / runner_slug / f"{stamp}{label_suffix}"
    run_dir.mkdir(parents=True, exist_ok=False)

    for name in REQUIRED_FILES:
        shutil.copy2(dropzone / name, run_dir / name)

    index_payload = {
        "schema": "news_repro_archive_run_v1",
        "archived_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runner_id": runner_id,
        "runner_slug": runner_slug,
        "source_dropzone": str(dropzone),
        "archive_dir": str(run_dir),
        "files": REQUIRED_FILES,
    }
    (run_dir / "_archive_index.json").write_text(json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
