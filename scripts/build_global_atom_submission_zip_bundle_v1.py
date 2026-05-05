#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build final submission zip bundle from camera-ready and artifacts.")
    ap.add_argument("--bundle-json", default="docs/final/artifacts/global_atom_submission_bundle_latest.json")
    ap.add_argument("--camera-ready-pack-json", default="docs/final/artifacts/global_atom_camera_ready_pack_latest.json")
    ap.add_argument("--camera-ready-polish-json", default="docs/final/artifacts/global_atom_camera_ready_polish_latest.json")
    ap.add_argument("--output-zip", default="")
    ap.add_argument("--manifest-out-json", default="docs/final/artifacts/global_atom_submission_zip_bundle_latest.json")
    args = ap.parse_args()

    bundle_path = resolve(args.bundle_json)
    cr_pack_path = resolve(args.camera_ready_pack_json)
    cr_polish_path = resolve(args.camera_ready_polish_json)
    for p in (bundle_path, cr_pack_path, cr_polish_path):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    bundle = load(bundle_path)
    cr_pack = load(cr_pack_path)
    cr_polish = load(cr_polish_path)

    files: list[Path] = []
    files.extend([bundle_path, cr_pack_path, cr_polish_path])

    packet = bundle.get("artifact_packet") if isinstance(bundle.get("artifact_packet"), dict) else {}
    for item in packet.values():
        if isinstance(item, dict) and item.get("path"):
            p = Path(str(item["path"]))
            if p.is_file():
                files.append(p)

    for key in ("paper_draft_md", "appendix_md"):
        p = Path(str(((cr_pack.get("outputs") or {}).get(key)) or ""))
        if p.is_file():
            files.append(p)
    for key in ("paper_out_md", "appendix_out_md"):
        p = Path(str(((cr_polish.get("outputs") or {}).get(key)) or ""))
        if p.is_file():
            files.append(p)

    # de-duplicate while preserving order
    uniq: list[Path] = []
    seen: set[str] = set()
    for p in files:
        s = str(p.resolve())
        if s in seen:
            continue
        seen.add(s)
        uniq.append(p)

    if args.output_zip.strip():
        zip_path = resolve(args.output_zip)
    else:
        zip_path = resolve(f"docs/final/artifacts/global_atom_submission_bundle_{stamp()}.zip")
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in uniq:
            rel = p.resolve().relative_to(ROOT.resolve())
            zf.write(p, arcname=str(rel).replace("\\", "/"))

    manifest_out = resolve(args.manifest_out_json)
    out = {
        "schema": "global_atom_submission_zip_bundle_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "zip_path": str(zip_path),
        "file_count": len(uniq),
        "files": [str(p) for p in uniq],
        "inputs": {
            "bundle_json": str(bundle_path),
            "camera_ready_pack_json": str(cr_pack_path),
            "camera_ready_polish_json": str(cr_polish_path),
        },
    }
    manifest_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(zip_path))
    print(str(manifest_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

