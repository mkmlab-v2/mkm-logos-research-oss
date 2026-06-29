#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build multi-anchor comparative theology digest from curated seed manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_comparative_theology_panorama_v1 import build as build_panorama

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/comparative_theology_seeds/manifest_job_prologue_v1.json"
DEFAULT_CROSS_REF = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"

SCHEMA_VERSION = "comparative_theology_panorama_digest_v1"
GENERATOR = "build_comparative_theology_panorama_digest_v1.py@1.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_digest(*, manifest: dict[str, Any], cross_ref: dict[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for rel in manifest.get("seeds") or []:
        seed_path = ROOT / str(rel)
        seed = _load(seed_path)
        pano = build_panorama(seed=seed, cross_ref=cross_ref)
        pano["seed_path"] = str(seed_path.relative_to(ROOT)).replace("\\", "/")
        entries.append(pano)

    primary_ref = str(manifest.get("primary_anchor_ref") or "Job.1.6")
    primary = next((e for e in entries if e.get("anchor_ref") == primary_ref), entries[0] if entries else {})

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "issue_id": manifest.get("issue_id"),
        "primary_anchor_ref": primary_ref,
        "panorama_entries": entries,
        "entry_count": len(entries),
        "disclaimer": primary.get("disclaimer"),
        "fact_lock": primary.get("fact_lock"),
        "reproduce": {
            "command": "py scripts/build_comparative_theology_panorama_digest_v1.py",
            "manifest_path": str(DEFAULT_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build comparative theology panorama digest v1.")
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--cross-ref-json", type=Path, default=DEFAULT_CROSS_REF)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    args = ap.parse_args()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    manifest = _load(_p(args.manifest_json))
    cross_ref = _load(_p(args.cross_ref_json)) if _p(args.cross_ref_json).is_file() else {}
    doc = build_digest(manifest=manifest, cross_ref=cross_ref)
    out = _p(args.out_artifact)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(out), "entry_count": doc["entry_count"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
