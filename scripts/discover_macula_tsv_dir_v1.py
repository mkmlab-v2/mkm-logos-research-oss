#!/usr/bin/env python3
"""Discover MACULA TSV directory — env first, then known vault/workspace paths."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/macula_tsv_dir_discovery_v1_latest.json"

MACULA_HEADER_HINTS = ("book", "chapter", "verse", "lemma", "word", "greek", "hebrew", "strong")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _candidate_dirs() -> list[Path]:
    raw_paths: list[str | Path] = [
        os.getenv("MACULA_TSV_DIR", "").strip(),
        os.getenv("MKM_MACULA_TSV_DIR", "").strip(),
        ROOT / "data" / "macula",
        ROOT / "data" / "macula_tsv",
        ROOT / "memory" / "v2" / "btrack" / "raw_feeds" / "macula",
        Path(r"G:\공유 드라이브\MKM_DATA_VAULT\vault\macula"),
        Path(r"G:\공유 드라이브\MKM_DATA_VAULT\macula"),
        Path(r"G:/MKM_DATA_VAULT/vault/macula"),
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for raw in raw_paths:
        if not raw:
            continue
        p = Path(raw)
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _score_tsv_dir(path: Path) -> dict[str, Any] | None:
    if not path.is_dir():
        return None
    tsv_files = sorted(path.glob("*.tsv"))
    if not tsv_files:
        return None
    macula_like = 0
    for tsv in tsv_files[:5]:
        try:
            head = tsv.read_text(encoding="utf-8-sig", errors="replace").splitlines()[:1]
            if not head:
                continue
            cols = {c.strip().lower() for c in head[0].split("\t")}
            if any(h in cols for h in MACULA_HEADER_HINTS):
                macula_like += 1
        except OSError:
            continue
    if macula_like == 0 and len(tsv_files) < 1:
        return None
    return {
        "path": str(path),
        "tsv_count": len(tsv_files),
        "macula_like_samples": macula_like,
        "score": macula_like * 10 + len(tsv_files),
    }


def discover() -> dict[str, Any]:
    scanned: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for cand in _candidate_dirs():
        row = _score_tsv_dir(cand)
        if row:
            scanned.append(row)
            if best is None or row["score"] > best["score"]:
                best = row
    return {
        "schema": "macula_tsv_dir_discovery_v1",
        "generated_at_utc": _utc(),
        "found": best is not None,
        "best": best,
        "candidates_scored": scanned,
        "reproduce": "py scripts/discover_macula_tsv_dir_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--print-path", action="store_true", help="Print best path only (for shell capture)")
    args = ap.parse_args()

    doc = discover()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.print_path and doc.get("best"):
        print(doc["best"]["path"])
        return 0

    print(json.dumps({"ok": True, "found": doc["found"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
