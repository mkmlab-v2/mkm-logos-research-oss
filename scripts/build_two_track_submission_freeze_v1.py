#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze current two-track submission artifacts.")
    ap.add_argument(
        "--manifest-out",
        default="docs/final/artifacts/two_track_submission_freeze_latest.json",
    )
    ap.add_argument(
        "--freeze-root",
        default="docs/final/artifacts/freeze",
    )
    args = ap.parse_args()

    files = [
        "docs/final/artifacts/two_track_submission_evidence_bundle_latest.json",
        "docs/final/artifacts/two_track_submission_draft_latest.json",
        "docs/final/artifacts/two_track_submission_camera_ready_latest.json",
        "docs/final/artifacts/two_track_falsification_suite_latest.json",
        "docs/final/artifacts/two_track_falsification_sensitivity_latest.json",
        "docs/final/artifacts/two_track_falsification_boundary_report_latest.json",
        "docs/final/artifacts/two_track_raw_oos_readiness_latest.json",
        "docs/final/artifacts/two_track_statistical_significance_report_latest.json",
    ]

    stamp = _stamp()
    freeze_root = _resolve(args.freeze_root)
    freeze_dir = freeze_root / f"two_track_submission_{stamp}"
    freeze_dir.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in files:
        src = _resolve(rel)
        if not src.is_file():
            missing.append(str(src))
            continue
        dst = freeze_dir / src.name
        shutil.copy2(src, dst)
        generated_at = None
        try:
            generated_at = _load_json(src).get("generated_at_utc")
        except Exception:
            generated_at = None
        copied.append(
            {
                "source": str(src),
                "frozen_copy": str(dst),
                "generated_at_utc": generated_at,
            }
        )

    manifest = {
        "schema": "two_track_submission_freeze_v1",
        "generated_at_utc": _utc_now(),
        "freeze_stamp": stamp,
        "freeze_dir": str(freeze_dir),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "artifacts": copied,
        "missing_artifacts": missing,
    }

    manifest_path = _resolve(args.manifest_out)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(manifest_path))
    return 0 if len(missing) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

