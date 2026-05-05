#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
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
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit submission zip integrity and required contents.")
    ap.add_argument("--zip-manifest-json", default="docs/final/artifacts/global_atom_submission_zip_bundle_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_submission_release_audit_latest.json")
    args = ap.parse_args()

    zp = resolve(args.zip_manifest_json)
    op = resolve(args.output_json)
    if not zp.is_file():
        raise SystemExit(f"missing zip manifest: {zp}")

    zdoc = load(zp)
    zip_path = Path(str(zdoc.get("zip_path", "")))
    if not zip_path.is_file():
        raise SystemExit(f"missing zip file: {zip_path}")

    required_suffixes = [
        "global_atom_network_academic_onepager_latest.json",
        "global_atom_kdd_submission_template_latest.json",
        "global_atom_submission_bundle_latest.json",
        "global_atom_full_canon_batch_report_latest.json",
        "global_atom_camera_ready_paper_polished_latest.md",
        "global_atom_camera_ready_appendix_polished_latest.md",
    ]

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    missing = []
    for suffix in required_suffixes:
        if not any(name.endswith(suffix) for name in names):
            missing.append(suffix)

    sha = sha256_file(zip_path)
    ok = len(missing) == 0
    out = {
        "schema": "global_atom_submission_release_audit_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "zip_path": str(zip_path),
        "zip_size_bytes": zip_path.stat().st_size,
        "zip_sha256": sha,
        "zip_entry_count": len(names),
        "required_suffixes": required_suffixes,
        "missing_required_suffixes": missing,
        "audit_status": "PASS" if ok else "FAIL",
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

