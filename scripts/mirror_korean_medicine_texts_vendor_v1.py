#!/usr/bin/env python3
"""Mirror Raphael-KR/korean-medicine-texts — pin commit SHA [HYPO].

Clinician lane only · read-only vendor · no PersonaDiary join.

  py scripts/mirror_korean_medicine_texts_vendor_v1.py
  py scripts/mirror_korean_medicine_texts_vendor_v1.py --skip-clone --vendor-root tests/fixtures/km_classics_vendor_stub_hypo_v1
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/Raphael-KR/korean-medicine-texts.git"
DEFAULT_VENDOR = ROOT / "vendor" / "korean-medicine-texts"
DEFAULT_OUT = ROOT / "reports" / "km_classics_vendor_mirror_v1_latest.json"
SCHEMA = "km_classics_vendor_mirror_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(args: list[str], *, cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def _git_head_sha(vendor_root: Path) -> str:
    return _run_git(["rev-parse", "HEAD"], cwd=vendor_root)


def _git_short_sha(vendor_root: Path) -> str:
    return _run_git(["rev-parse", "--short", "HEAD"], cwd=vendor_root)


def ensure_vendor_clone(vendor_root: Path) -> str:
    if (vendor_root / ".git").is_dir():
        _run_git(["fetch", "--depth", "1", "origin"], cwd=vendor_root)
        _run_git(["checkout", "main"], cwd=vendor_root)
        _run_git(["pull", "--ff-only", "origin", "main"], cwd=vendor_root)
        action = "updated"
    else:
        vendor_root.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(vendor_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git clone failed ({proc.returncode}): {proc.stderr.strip()}")
        action = "cloned"
    return action


def build_mirror_report(vendor_root: Path, *, clone_action: str | None) -> dict[str, Any]:
    catalog_path = vendor_root / "catalog.json"
    texts_dir = vendor_root / "texts"
    source_count = 0
    if texts_dir.is_dir():
        source_count = sum(1 for p in texts_dir.glob("*/source.md") if p.is_file())

    return {
        "schema": SCHEMA,
        "version": 1,
        "hypothesis_tier": "B",
        "research_only": True,
        "clinician_lane_only": True,
        "personadiary_join": False,
        "generated_at_utc": _utc_now(),
        "upstream_url": REPO_URL,
        "vendor_root": str(vendor_root.resolve()),
        "clone_action": clone_action or "verified_existing",
        "commit_sha": _git_head_sha(vendor_root),
        "commit_sha_short": _git_short_sha(vendor_root),
        "catalog_present": catalog_path.is_file(),
        "source_md_count": source_count,
        "boundary_ack": (
            "Read-only mirror for clinician citation index — not bundled in repo commits"
        ),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vendor-root", type=Path, default=DEFAULT_VENDOR)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--skip-clone",
        action="store_true",
        help="Do not fetch/clone; require existing vendor_root (stub ok for pytest).",
    )
    args = ap.parse_args()
    vendor_root = args.vendor_root.resolve()

    try:
        if args.skip_clone:
            if not vendor_root.is_dir():
                print(f"vendor_root_missing: {vendor_root}", file=sys.stderr)
                return 1
            clone_action = None
            if (vendor_root / ".git").is_dir():
                commit_sha = _git_head_sha(vendor_root)
            else:
                commit_sha = "stub-no-git"
            doc = build_mirror_report(vendor_root, clone_action=clone_action)
            if commit_sha == "stub-no-git":
                doc["commit_sha"] = "stub-no-git"
                doc["commit_sha_short"] = "stub"
                doc["clone_action"] = "stub_fixture"
        else:
            clone_action = ensure_vendor_clone(vendor_root)
            doc = build_mirror_report(vendor_root, clone_action=clone_action)
    except (RuntimeError, FileNotFoundError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "clone_action": doc.get("clone_action"),
                "commit_sha_short": doc.get("commit_sha_short"),
                "source_md_count": doc.get("source_md_count"),
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
