#!/usr/bin/env python3
"""Fetch Gnosis KG v0.9.3 release JSON into storage/external_kg [HYPO].

Downloads greek-words.json + extracts hebrew-words.json/strongs.json from tar.gz.
No automatic merge into logos_lemma_verse_edges — run ingest script after fetch.
License: Gnosis CC-BY-SA 4.0 — verify upstream SOURCES.md before redistributing.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "storage/external_kg/gnosis_v0.9.3"
DEFAULT_REPORT = ROOT / "reports/logos_gnosis_kg_fetch_v1_latest.json"
RELEASE_TAG = "v0.9.3"
REPO = "spearssoftware/gnosis"
TAR_NAME = "gnosis-v0.9.3.tar.gz"
EXTRACT_FROM_TAR = ("hebrew-words.json", "strongs.json")
DIRECT_ASSETS = ("greek-words.json",)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    tail = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode, tail


def fetch_release(dest: Path, *, skip_download: bool = False) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []

    if not skip_download:
        for pattern in (TAR_NAME, *DIRECT_ASSETS):
            rc, tail = _run(
                [
                    "gh",
                    "release",
                    "download",
                    RELEASE_TAG,
                    "--repo",
                    REPO,
                    "--pattern",
                    pattern,
                    "--dir",
                    str(dest),
                ],
                ROOT,
            )
            steps.append({"pattern": pattern, "exit_code": rc, "ok": rc == 0, "tail": tail[-300:]})
            if rc != 0:
                raise SystemExit(f"gh release download failed for {pattern}: {tail[-400:]}")

    tar_path = dest / TAR_NAME
    extracted: list[str] = []
    if tar_path.is_file():
        with tarfile.open(tar_path, "r:gz") as tf:
            members = {m.name.lstrip("./"): m for m in tf.getmembers() if m.isfile()}
            for name in EXTRACT_FROM_TAR:
                member = members.get(name)
                if member is None:
                    steps.append({"extract": name, "ok": False, "reason": "missing_in_tar"})
                    continue
                out = dest / name
                with tf.extractfile(member) as src, out.open("wb") as dst:
                    assert src is not None
                    shutil.copyfileobj(src, dst)
                extracted.append(name)
                steps.append({"extract": name, "ok": True, "bytes": out.stat().st_size})

    files = {}
    for fname in (*DIRECT_ASSETS, *EXTRACT_FROM_TAR):
        p = dest / fname
        files[fname] = {"path": _rel(p), "exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}

    ok = all(files[f]["exists"] for f in (*DIRECT_ASSETS, *EXTRACT_FROM_TAR))
    return {
        "schema": "logos_gnosis_kg_fetch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "release_tag": RELEASE_TAG,
        "repo": REPO,
        "license": "CC-BY-SA-4.0",
        "dest_dir": _rel(dest),
        "steps": steps,
        "files": files,
        "ok": ok,
        "reproduce": f"py scripts/fetch_logos_gnosis_kg_release_v1.py --dest {dest.as_posix()}",
        "next": "py scripts/ingest_logos_gnosis_kg_lemma_edges_v1.py --gnosis-dir "
        + _rel(dest)
        + " --ack-license-cc-by-sa-4 --max-edges 350000",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument(
        "--skip-download",
        action="store_true",
        help="Only extract from existing tar.gz in dest (offline re-extract)",
    )
    args = ap.parse_args()

    doc = fetch_release(args.dest, skip_download=args.skip_download)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "dest": doc["dest_dir"], "report": str(args.report)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
