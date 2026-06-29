#!/usr/bin/env python3
"""Fetch Sinew dataset (HF) into storage/external_kg [HYPO].

License: Sinew compilation CC-BY-4.0 — attribute OpenBible.info.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "storage/external_kg/sinew_v1"
DEFAULT_REPORT = ROOT / "reports/logos_sinew_xref_fetch_v1_latest.json"
HF_REPO = "LucasGalhardoLima/sinew"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def fetch_sinew(dest: Path, *, skip_download: bool = False) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []
    if not skip_download:
        rc = subprocess.run(
            ["hf", "download", HF_REPO, "--repo-type", "dataset", "--local-dir", str(dest)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        steps.append({"hf_download": HF_REPO, "exit_code": rc, "ok": rc == 0})
        if rc != 0:
            raise SystemExit(f"hf download failed rc={rc}")

    required = ["sinew.sqlite", "parquet/connections.parquet", "LICENSE", "sources.lock.json"]
    files = {}
    for name in required:
        p = dest / name
        files[name] = {"path": _rel(p), "exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}

    ok = all(files[n]["exists"] for n in required)
    return {
        "schema": "logos_sinew_xref_fetch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "hf_repo": HF_REPO,
        "license": "CC-BY-4.0",
        "dest_dir": _rel(dest),
        "steps": steps,
        "files": files,
        "ok": ok,
        "reproduce": f"py scripts/fetch_logos_sinew_xref_release_v1.py --dest {dest.as_posix()}",
        "next": "py scripts/ingest_logos_sinew_xref_edges_v1.py --sinew-dir "
        + _rel(dest)
        + " --ack-license-cc-by-4",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    doc = fetch_sinew(args.dest, skip_download=args.skip_download)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "dest": doc["dest_dir"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
