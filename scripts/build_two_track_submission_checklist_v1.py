#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def item(path: Path) -> dict[str, Any]:
    exists = path.is_file()
    generated = None
    if exists:
        try:
            generated = load(path).get("generated_at_utc")
        except Exception:
            generated = None
    return {"path": str(path), "exists": exists, "generated_at_utc": generated}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-page JSON checklist for submission freeze package.")
    ap.add_argument("--freeze-manifest-json", default="docs/final/artifacts/two_track_submission_freeze_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/two_track_submission_checklist_latest.json")
    args = ap.parse_args()

    mp = resolve(args.freeze_manifest_json)
    op = resolve(args.output_json)
    if not mp.is_file():
        raise SystemExit(f"missing freeze manifest: {mp}")

    manifest = load(mp)
    freeze_dir = Path(str(manifest.get("freeze_dir", "")))
    freeze_exists = freeze_dir.is_dir()
    copied_count = int(manifest.get("copied_count", 0) or 0)
    missing_count = int(manifest.get("missing_count", 0) or 0)

    key_files = {
        "evidence_bundle": freeze_dir / "two_track_submission_evidence_bundle_latest.json",
        "submission_draft": freeze_dir / "two_track_submission_draft_latest.json",
        "camera_ready": freeze_dir / "two_track_submission_camera_ready_latest.json",
        "falsification_suite": freeze_dir / "two_track_falsification_suite_latest.json",
        "falsification_sensitivity": freeze_dir / "two_track_falsification_sensitivity_latest.json",
        "falsification_boundary": freeze_dir / "two_track_falsification_boundary_report_latest.json",
        "raw_oos_readiness": freeze_dir / "two_track_raw_oos_readiness_latest.json",
        "significance_report": freeze_dir / "two_track_statistical_significance_report_latest.json",
    }
    check = {k: item(v) for k, v in key_files.items()}
    all_present = all(v["exists"] for v in check.values()) and freeze_exists and missing_count == 0

    out = {
        "schema": "two_track_submission_checklist_v1",
        "generated_at_utc": now(),
        "freeze_manifest_json": str(mp),
        "freeze_stamp": manifest.get("freeze_stamp"),
        "freeze_dir": str(freeze_dir),
        "freeze_dir_exists": freeze_exists,
        "freeze_copied_count": copied_count,
        "freeze_missing_count": missing_count,
        "artifact_checklist": check,
        "submission_ready": all_present,
        "repro_commands": [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_aramaic_mvp_chain_v1.ps1",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_two_track_submission_pack_v1.ps1 -StrictPrereqs",
            "py scripts/build_two_track_submission_freeze_v1.py",
        ],
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

