from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_WATCH_PATHS = [
    ".env",
    "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
    "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
]


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_snapshot(paths: list[str]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for raw in paths:
        p = Path(raw)
        key = p.as_posix()
        if not p.exists():
            files[key] = {"exists": False, "sha256": ""}
            continue
        files[key] = {"exists": True, "sha256": sha256_file(p)}
    return {
        "schema": "security_integrity_manifest_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def compare_snapshot(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    changed: list[str] = []
    baseline_files = baseline.get("files", {})
    current_files = current.get("files", {})
    keys = sorted(set(list(baseline_files.keys()) + list(current_files.keys())))
    for key in keys:
        if baseline_files.get(key) != current_files.get(key):
            changed.append(key)

    status = "GREEN" if not changed else "RED"
    return {
        "schema": "security_integrity_status_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "changed_paths": changed,
        "changed_count": len(changed),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect integrity drift for critical local files."
    )
    parser.add_argument(
        "--mode",
        choices=["snapshot", "check"],
        required=True,
        help="snapshot: write baseline, check: compare current against baseline",
    )
    parser.add_argument(
        "--watch-path",
        action="append",
        default=[],
        help="Additional watch path (repeatable).",
    )
    parser.add_argument(
        "--manifest-path",
        default="reports/security_integrity_manifest_v1.json",
        help="Baseline manifest path.",
    )
    parser.add_argument(
        "--status-path",
        default="reports/security_integrity_status_latest.json",
        help="Status output path for check mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    watch_paths = DEFAULT_WATCH_PATHS + args.watch_path
    current = build_snapshot(watch_paths)
    manifest_path = Path(args.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    if args.mode == "snapshot":
        manifest_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"security_snapshot_written={manifest_path.as_posix()}")
        return 0

    if not manifest_path.exists():
        print("security_check_failed=missing_manifest")
        return 3

    baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = compare_snapshot(current=current, baseline=baseline)
    status_path = Path(args.status_path)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"security_status={status['status']} changed_count={status['changed_count']}")
    return 0 if status["status"] == "GREEN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
