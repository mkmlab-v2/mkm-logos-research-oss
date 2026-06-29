#!/usr/bin/env python3
"""Zip customer VPC deploy package: air-gap bundle + exe + checklist + runbook [HYPO] B-track."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZIP = ROOT / "reports/edge_encoder_vpc_deploy_package_v1_latest.zip"
DEFAULT_META = ROOT / "docs/final/artifacts/edge_encoder_vpc_deploy_package_v1_latest.json"
BUNDLE_DIR = ROOT / "reports/edge_encoder_air_gap_bundle_v1_latest"
PORTABLE_DIR = ROOT / "reports/edge_encoder_sdk_portable_launcher_v1_latest"
EXE = ROOT / "reports/edge_encoder_sdk_pyinstaller_v1_latest/dist/mkm-edge-encoder-sdk.exe"

STATIC_FILES: tuple[str, ...] = (
    "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json",
    "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html",
    "docs/final/artifacts/edge_encoder_spec_v1_latest.json",
    "docs/final/artifacts/edge_encoder_pyinstaller_readiness_v1_latest.json",
    "docs/final/EDGE_ENCODER_SPEC_DRAFT_V1.md",
    "reports/edge_encoder_air_gap_poc_pack_v1_latest.json",
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _zip_dir(zf: zipfile.ZipFile, src_dir: Path, arc_prefix: str) -> list[str]:
    included: list[str] = []
    if not src_dir.is_dir():
        return included
    for path in sorted(src_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = f"{arc_prefix}/{path.relative_to(src_dir).as_posix()}"
        zf.write(path, rel)
        included.append(rel)
    return included


def build_zip(*, zip_path: Path, require_exe: bool) -> dict[str, Any]:
    if not BUNDLE_DIR.is_dir():
        raise FileNotFoundError(f"missing air-gap bundle dir: {BUNDLE_DIR}")

    included: list[str] = []
    missing: list[str] = []
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        included.extend(_zip_dir(zf, BUNDLE_DIR, "air_gap_bundle"))
        included.extend(_zip_dir(zf, PORTABLE_DIR, "portable_launcher"))

        for rel in STATIC_FILES:
            src = ROOT / rel
            if not src.is_file():
                missing.append(rel)
                continue
            zf.write(src, rel.replace("\\", "/"))
            included.append(rel.replace("\\", "/"))

        if EXE.is_file():
            arc = "bin/mkm-edge-encoder-sdk.exe"
            zf.write(EXE, arc)
            included.append(arc)
        elif require_exe:
            raise FileNotFoundError(f"missing pyinstaller exe: {EXE}")

        readme = (
            "MKM Edge Encoder — customer VPC on-prem deploy package [HYPO]\n"
            f"generated_at_utc: {_utc()}\n"
            "send_gate: HOLD · ready_for_external_send: false\n"
            "original_bulk_sent: false — ship wire/wire_only_export.json fields only.\n"
            "FAIL-COMP-004: do not cite coord_wire ~156 tokens as global MASK 47% headline.\n"
            "Open reports/demo/edge_encoder_vpc_deploy_checklist_v1.html for operator steps.\n"
            "Smoke: bin/mkm-edge-encoder-sdk.exe encode-manifest (frozen path; roundtrip needs v2 HTTP stub).\n"
        )
        zf.writestr("00_README_VPC_DEPLOY.txt", readme)

    return {
        "schema": "edge_encoder_vpc_deploy_package_v1",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "original_bulk_sent": False,
        "zip_path": zip_path.relative_to(ROOT).as_posix(),
        "zip_sha256": _sha256(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "included_count": len(included),
        "missing_static_count": len(missing),
        "exe_included": EXE.is_file(),
        "bundle_dir": BUNDLE_DIR.relative_to(ROOT).as_posix(),
        "included_sample": included[:20],
        "missing_static": missing,
        "ok": len(missing) == 0 and bool(included),
        "fail_comp_004": "Do not merge COORD wire savings with MASK 47% / LTM 99% headlines.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip-out", type=Path, default=DEFAULT_ZIP)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--require-exe", action="store_true")
    args = ap.parse_args()
    meta = build_zip(zip_path=args.zip_out, require_exe=args.require_exe)
    args.meta_json.parent.mkdir(parents=True, exist_ok=True)
    args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": meta["ok"],
                "zip": meta["zip_path"],
                "exe_included": meta["exe_included"],
                "included": meta["included_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if meta["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
