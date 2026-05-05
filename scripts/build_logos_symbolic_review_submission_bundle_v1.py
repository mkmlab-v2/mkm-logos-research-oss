#!/usr/bin/env python3
"""Build submission bundle (zip + manifest) for Logos A-track review."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except Exception:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-zip", type=Path, default=ART / "logos_symbolic_review_submission_bundle_latest.zip")
    ap.add_argument("--out-manifest", type=Path, default=ART / "logos_symbolic_review_submission_bundle_manifest_latest.json")
    args = ap.parse_args()

    include_paths = [
        ART / "logos_symbolic_release_signoff_packet_latest.json",
        ART / "logos_symbolic_release_signoff_packet_latest.md",
        ART / "logos_symbolic_a_track_review_onepager_latest.md",
        ART / "logos_symbolic_paid_user_brief_latest.json",
        ART / "logos_symbolic_paid_user_brief_latest.md",
        ART / "logos_symbolic_paid_brief_stress_test_latest.json",
        ART / "logos_symbolic_paid_brief_stress_test_latest.md",
        ART / "logos_showroom_public_bundle_latest.json",
        ART / "logos_symbolic_event_human_approval_latest.json",
        ART / "logos_symbolic_event_track_a_candidate_latest.json",
        ART / "logos_symbolic_event_promotion_gate_latest.json",
        ART / "logos_symbolic_revalidation_report_latest.json",
        ART / "logos_symbolic_data_hygiene_audit_latest.json",
        ART / "logos_symbolic_source_performance_breakdown_latest.json",
    ]

    entries: list[dict[str, Any]] = []
    for p in include_paths:
        if p.is_file():
            entries.append(
                {
                    "path": str(p.resolve()).replace("\\", "/"),
                    "name": p.name,
                    "size_bytes": _size(p),
                    "sha256": _sha256(p),
                }
            )

    out_zip = Path(args.out_zip).resolve()
    out_manifest = Path(args.out_manifest).resolve()
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for e in entries:
            src = Path(e["path"])
            zf.write(src, arcname=e["name"])

    manifest = {
        "schema": "logos_symbolic_review_submission_bundle_manifest_v1",
        "generated_at_utc": _now(),
        "bundle_zip": str(out_zip).replace("\\", "/"),
        "bundle_sha256": _sha256(out_zip),
        "file_count": len(entries),
        "files": entries,
        "constraints": {
            "auto_a_track_bridge": False,
            "auto_live_trigger": False,
            "manual_gate_required": True,
        },
    }
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_zip))
    print(str(out_manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

