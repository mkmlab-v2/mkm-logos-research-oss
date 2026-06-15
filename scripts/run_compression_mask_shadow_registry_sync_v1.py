#!/usr/bin/env python3
"""[HYPO-3] Sync MASK shadow registry — manifest hashes + local mirror + staging pointers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_mask_shadow_registry_v1_lib import (  # noqa: E402
    build_registry,
    mirror_registry_files,
    write_registry_artifacts,
)

DEFAULT_REPORT = ROOT / "reports/compression_mask_shadow_registry_v1_latest.json"
DEFAULT_STAGING = ROOT / "docs/final/artifacts/compression_mask_shadow_registry_staging_v1.json"
DEFAULT_MIRROR = ROOT / "storage/compression_shadow_registry_v1/mirror"


def main() -> int:
    ap = argparse.ArgumentParser(description="[HYPO-3] MASK shadow registry sync")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--staging-out", type=Path, default=DEFAULT_STAGING)
    ap.add_argument("--mirror-dir", type=Path, default=DEFAULT_MIRROR)
    ap.add_argument("--skip-mirror", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    registry = build_registry(workspace_root=args.workspace_root)
    agg = registry["aggregate"]
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "aggregate": agg}, ensure_ascii=False))
        return 0 if agg["all_entries_present"] else 1

    write_registry_artifacts(registry, report_path=args.report_out, staging_path=args.staging_out)
    # Self-pointer for v2 stub env swap (written after artifact exists).
    registry["staging_env_pointers"]["MKM_COMPRESSION_MASK_SHADOW_REGISTRY_JSON"] = args.staging_out.relative_to(
        args.workspace_root
    ).as_posix()
    write_registry_artifacts(registry, report_path=args.report_out, staging_path=args.staging_out)
    mirror_summary: dict | None = None
    if not args.skip_mirror:
        mirror_summary = mirror_registry_files(
            registry,
            mirror_root=args.mirror_dir,
            workspace_root=args.workspace_root,
        )

    print(
        json.dumps(
            {
                "ok": True,
                "all_entries_present": agg["all_entries_present"],
                "git_head_sha": registry.get("git_head_sha"),
                "entry_count": agg["entry_count"],
                "report_out": str(args.report_out),
                "staging_out": str(args.staging_out),
                "mirror_copied": (mirror_summary or {}).get("copied_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if agg["all_entries_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
