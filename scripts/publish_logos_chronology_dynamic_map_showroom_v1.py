#!/usr/bin/env python3
"""Publish logos_chronology_dynamic_map artifact to showroom static paths."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src",
        default="docs/final/artifacts/logos_chronology_dynamic_map_v1_latest.json",
    )
    parser.add_argument(
        "--mvp-out",
        default=(
            "projects/bitcoin-trading/ops/windows-rehearsal/"
            "jemaai-cloud-mvp/showroom_logos_chronology_dynamic_map_v1.json"
        ),
    )
    parser.add_argument(
        "--artifact-out",
        default="docs/final/artifacts/showroom_logos_chronology_dynamic_map_v1_latest.json",
    )
    args = parser.parse_args()

    root = _root()
    src = root / args.src
    if not src.is_file():
        print(f"missing src: {src}")
        return 1

    mvp_out = root / args.mvp_out
    artifact_out = root / args.artifact_out
    mvp_out.parent.mkdir(parents=True, exist_ok=True)
    artifact_out.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, mvp_out)
    shutil.copy2(src, artifact_out)

    doc = json.loads(mvp_out.read_text(encoding="utf-8"))
    top = (doc.get("era_ranking") or [{}])[0] if isinstance(doc.get("era_ranking"), list) else {}
    report = {
        "schema": "publish_logos_chronology_dynamic_map_showroom_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mvp_out": str(mvp_out.relative_to(root)).replace("\\", "/"),
        "artifact_out": str(artifact_out.relative_to(root)).replace("\\", "/"),
        "primary_era_id": top.get("era_id"),
        "primary_score": top.get("score"),
        "ok": True,
    }
    out_report = root / "reports/publish_logos_chronology_dynamic_map_showroom_v1_latest.json"
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
