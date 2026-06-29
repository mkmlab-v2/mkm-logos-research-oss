#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consult or seed → resolve → 3 renders → personadiary adapt → publish manifest."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

CHAIN = ROOT / "scripts" / "run_integrated_wellness_solution_v2_chain_v1.py"
SEED_BUILDER = ROOT / "scripts" / "build_integrated_wellness_seed_from_consult_v1.py"
PERSONADIARY_ADAPT = ROOT / "scripts" / "adapt_integrated_wellness_personadiary_export_v1.py"
DEFAULT_OUT = ROOT / "reports" / "integrated_wellness_solution_v2_chain"


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout or f"failed: {' '.join(cmd)}")


def publish(
    *,
    seed_path: Path,
    out_dir: Path,
    no1kmedi_public: Path | None,
    personadiary_public: Path | None,
    mkmlife_public: Path | None,
    validate: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    chain_cmd = [sys.executable, str(CHAIN), "--seed-json", str(seed_path), "--out-dir", str(out_dir)]
    if validate:
        chain_cmd.append("--validate")
    _run(chain_cmd)

    resolved = out_dir / "resolved_latest.json"
    pd_render = out_dir / "render_personadiary_latest.json"
    pd_adapted = out_dir / "personadiary_daily_package_latest.json"
    _run(
        [
            sys.executable,
            str(PERSONADIARY_ADAPT),
            "--render-json",
            str(pd_render),
            "--resolved-json",
            str(resolved),
            "--out-json",
            str(pd_adapted),
        ]
    )

    mkmlife_md = out_dir / "mkmlife_report_latest.md"
    mkmlife_json = out_dir / "render_mkmlife_latest.json"
    if mkmlife_json.is_file():
        doc = json.loads(mkmlife_json.read_text(encoding="utf-8-sig"))
        mkmlife_md.write_text(doc.get("body_markdown", "") + "\n", encoding="utf-8")

    copies: dict[str, str] = {}
    if no1kmedi_public:
        no1kmedi_public.mkdir(parents=True, exist_ok=True)
        dst = no1kmedi_public / "integrated_wellness_no1kmedi_latest.json"
        dst.write_text((out_dir / "render_no1kmedi_latest.json").read_text(encoding="utf-8"), encoding="utf-8")
        copies["no1kmedi"] = str(dst)

    if personadiary_public:
        personadiary_public.mkdir(parents=True, exist_ok=True)
        dst = personadiary_public / "personadiary_daily_response_package_v1.json"
        dst.write_text(pd_adapted.read_text(encoding="utf-8"), encoding="utf-8")
        copies["personadiary"] = str(dst)

    if mkmlife_public and mkmlife_json.is_file():
        mkmlife_public.mkdir(parents=True, exist_ok=True)
        json_dst = mkmlife_public / "integrated_wellness_mkmlife_report_v1.json"
        json_dst.write_text(mkmlife_json.read_text(encoding="utf-8"), encoding="utf-8")
        copies["mkmlife_json"] = str(json_dst)
        if mkmlife_md.is_file():
            md_dst = mkmlife_public / "integrated_wellness_mkmlife_report_v1.md"
            md_dst.write_text(mkmlife_md.read_text(encoding="utf-8"), encoding="utf-8")
            copies["mkmlife_md"] = str(md_dst)

    manifest = {
        "ok": True,
        "seed": str(seed_path),
        "out_dir": str(out_dir),
        "resolved": str(resolved),
        "personadiary_package": str(pd_adapted),
        "mkmlife_markdown": str(mkmlife_md) if mkmlife_md.is_file() else None,
        "copies": copies,
    }
    manifest_path = out_dir / "publish_manifest_latest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish IWS v2 exports to app static paths")
    parser.add_argument("--seed-json", type=Path)
    parser.add_argument("--consult-json", type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no1kmedi-public", type=Path)
    parser.add_argument("--personadiary-public", type=Path)
    parser.add_argument("--mkmlife-public", type=Path)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    seed_path = args.seed_json
    if args.consult_json:
        seed_path = out_dir / "seed_from_consult.json"
        _run(
            [
                sys.executable,
                str(SEED_BUILDER),
                "--consult-json",
                str(args.consult_json),
                "--out-json",
                str(seed_path),
            ]
        )
    if not seed_path or not seed_path.is_file():
        raise SystemExit("seed-json or consult-json required")

    manifest = publish(
        seed_path=seed_path,
        out_dir=out_dir,
        no1kmedi_public=args.no1kmedi_public,
        personadiary_public=args.personadiary_public,
        mkmlife_public=args.mkmlife_public,
        validate=args.validate,
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
