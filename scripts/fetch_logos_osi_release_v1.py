#!/usr/bin/env python3
"""Fetch Open Scripture Intelligence graph/canonical slices [HYPO].

Downloads graph/edges.jsonl + canonical/books.json + LICENSE from GitHub raw.
License: MIT (structure) + public-domain translations — verify upstream LICENSE.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = ROOT / "storage/external_kg/osi_v1"
DEFAULT_REPORT = ROOT / "reports/logos_osi_fetch_v1_latest.json"
REPO = "echology-io/open-scripture-intelligence"
BRANCH = "main"
ASSETS = (
    "graph/edges.jsonl",
    "canonical/books.json",
    "LICENSE_NOTES.md",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _download(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "mkm-logos-osi-fetch-v1"})
    with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as out:
        out.write(resp.read())
    return {"url": url, "path": _rel(dest), "bytes": dest.stat().st_size, "ok": dest.is_file()}


def fetch_osi(dest: Path, *, skip_download: bool = False) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []
    if not skip_download:
        for rel_path in ASSETS:
            url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{rel_path}"
            out = dest / rel_path.replace("/", "__")
            if rel_path == "graph/edges.jsonl":
                out = dest / "edges.jsonl"
            elif rel_path == "canonical/books.json":
                out = dest / "books.json"
            elif rel_path == "LICENSE_NOTES.md":
                out = dest / "LICENSE_NOTES.md"
            try:
                row = _download(url, out)
                row["asset"] = rel_path
                row["ok"] = out.is_file() and out.stat().st_size > 0
                steps.append(row)
            except OSError as exc:
                steps.append({"asset": rel_path, "ok": False, "error": str(exc)})
    else:
        for rel_path in ("canonical/books.json", "LICENSE_NOTES.md"):
            out = dest / ("books.json" if "books" in rel_path else "LICENSE_NOTES.md")
            if out.is_file():
                continue
            url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{rel_path}"
            try:
                row = _download(url, out)
                row["asset"] = rel_path
                row["ok"] = out.is_file() and out.stat().st_size > 0
                steps.append(row)
            except OSError as exc:
                steps.append({"asset": rel_path, "ok": False, "error": str(exc)})

    files = {}
    for name in ("edges.jsonl", "books.json", "LICENSE_NOTES.md"):
        p = dest / name
        files[name] = {"path": _rel(p), "exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}

    ok = files["edges.jsonl"]["exists"] and files["LICENSE_NOTES.md"]["exists"]
    return {
        "schema": "logos_osi_fetch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "repo": REPO,
        "branch": BRANCH,
        "license_hint": "MIT structure + PD translations",
        "dest_dir": _rel(dest),
        "steps": steps,
        "files": files,
        "ok": ok,
        "reproduce": f"py scripts/fetch_logos_osi_release_v1.py --dest {dest.as_posix()}",
        "next": f"py scripts/ingest_logos_osi_xref_edges_v1.py --osi-dir {_rel(dest)} --ack-license-mit-pd",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    doc = fetch_osi(args.dest, skip_download=args.skip_download)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "out": str(args.report), "dest": str(args.dest)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
