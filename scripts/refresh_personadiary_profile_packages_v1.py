#!/usr/bin/env python3
"""Build PersonaDiary daily packages for each profile in profile_registry_v1.json."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "personadiary" / "profile_registry_v1.json"
FORTUNE_SCRIPT = ROOT / "scripts" / "build_commander_daily_fortune_v1.py"
ASSEMBLE_SCRIPT = ROOT / "scripts" / "assemble_personadiary_daily_response_package_v1.py"
NO1K_PUBLIC = ROOT / "projects" / "no1kmedi" / "public" / "data"


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def refresh_all(
    *,
    registry_path: Path,
    skip_regenerate: bool,
    profile_ids: list[str] | None,
) -> Dict[str, Any]:
    reg = _read_json(registry_path)
    if reg.get("schema") != "personadiary_profile_registry_v1":
        raise SystemExit(f"expected personadiary_profile_registry_v1: {registry_path}")

    profiles: Dict[str, Any] = reg.get("profiles") or {}
    default_id = str(reg.get("default_profile_id") or "commander")
    ids = profile_ids or list(profiles.keys())
    built: Dict[str, str] = {}

    for pid in ids:
        meta = profiles.get(pid)
        if not isinstance(meta, dict):
            print(f"SKIP unknown profile_id={pid}", file=sys.stderr)
            continue
        profile_json = ROOT / str(meta["profile_json"])
        if not profile_json.is_file():
            raise SystemExit(f"missing profile_json for {pid}: {profile_json}")

        fortune_out = ROOT / "reports" / f"personadiary_fortune_{pid}_latest.json"
        pkg_artifact = (
            ROOT / "docs" / "final" / "artifacts" / f"personadiary_daily_response_package_{pid}_latest.json"
        )
        profiles_dir = NO1K_PUBLIC / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        pkg_public_profile = profiles_dir / f"{pid}.json"
        rel = str(
            meta.get("public_package_relpath")
            or "projects/no1kmedi/public/data/personadiary_daily_response_package_v1.json"
        )
        if rel.startswith("public/"):
            rel = f"projects/no1kmedi/{rel}"
        public_main = ROOT / rel
        public_main.parent.mkdir(parents=True, exist_ok=True)

        cmd_fortune = [
            sys.executable,
            str(FORTUNE_SCRIPT),
            "--profile-json",
            str(profile_json),
            "--out-json",
            str(fortune_out),
        ]
        if skip_regenerate:
            cmd_fortune.append("--skip-regenerate")
        _run(cmd_fortune)

        cmd_asm = [
            sys.executable,
            str(ASSEMBLE_SCRIPT),
            "--fortune-json",
            str(fortune_out),
            "--out-json",
            str(pkg_artifact),
        ]
        _run(cmd_asm)

        pkg_doc = _read_json(pkg_artifact)
        pkg_doc["profile_id"] = pid
        pkg_artifact.write_text(
            json.dumps(pkg_doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        shutil.copy2(pkg_artifact, pkg_public_profile)
        if pid == default_id:
            shutil.copy2(pkg_artifact, public_main)
            built["default_public"] = str(public_main)

        built[pid] = str(pkg_public_profile)
        print(f"OK profile={pid} -> {pkg_public_profile}")

    return {
        "schema": "personadiary_profile_refresh_report_v1",
        "default_profile_id": default_id,
        "built": built,
        "skip_regenerate": skip_regenerate,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry-json", type=Path, default=REGISTRY)
    ap.add_argument("--skip-regenerate", action="store_true")
    ap.add_argument("--profile-id", action="append", default=None, help="Repeatable; default all")
    ap.add_argument("--report-json", type=Path, default=None)
    args = ap.parse_args()

    report = refresh_all(
        registry_path=args.registry_json,
        skip_regenerate=args.skip_regenerate,
        profile_ids=args.profile_id,
    )
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"WROTE: {args.report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
