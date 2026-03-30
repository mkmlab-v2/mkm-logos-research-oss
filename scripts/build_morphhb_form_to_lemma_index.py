#!/usr/bin/env python3
"""Build normalized surface -> WLC lemma/morph index from OpenScriptures morphhb wlc/*.xml.

Streaming iterparse; DSS not in scope (WLC / MT alignment only per MASTER contract).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.build_original_language_master_atoms import _normalize_token  # noqa: E402

NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
W_TAG = f"{NS}w"

DEFAULT_WLC_DIR = ROOT / "vault" / "external_lexicon" / "sources" / "openscriptures-morphhb" / "wlc"
DEFAULT_INDEX_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "morphhb_norm_to_lemma_index_latest.json"

SKIP_BASENAMES = frozenset({"VerseMap.xml"})


def strongs_hints_from_lemma(lemma_raw: str) -> list[str]:
    """Extract H#### hints from morphhb lemma attribute (slash-separated parts)."""
    if not lemma_raw.strip():
        return []
    hints: list[str] = []
    for part in lemma_raw.split("/"):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"^(\d+)(\s+[a-z])?$", part, re.I)
        if not m:
            continue
        n = int(m.group(1), 10)
        if 1 <= n <= 99999:
            h = f"H{n}"
            if h not in hints:
                hints.append(h)
    return hints


def _surface_text(elem: ET.Element) -> str:
    return "".join(elem.itertext()).strip()


def iter_wlc_book_xml_files(wlc_dir: Path) -> list[Path]:
    if not wlc_dir.is_dir():
        return []
    out = sorted(p for p in wlc_dir.glob("*.xml") if p.name not in SKIP_BASENAMES)
    return out


def build_index(files: list[Path]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    # norm_key -> sig (lemma, morph, tuple(str_hints)) -> row
    buckets: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = defaultdict(dict)
    stats = {"w_tokens": 0, "files_read": 0}

    for path in files:
        stats["files_read"] += 1
        context = ET.iterparse(path, events=("end",))
        for _event, elem in context:
            if elem.tag != W_TAG:
                continue
            stats["w_tokens"] += 1
            lemma = (elem.get("lemma") or "").strip()
            morph = (elem.get("morph") or "").strip()
            surface = _surface_text(elem)
            if not surface:
                elem.clear()
                continue
            norm = _normalize_token(surface)
            if not norm:
                elem.clear()
                continue
            hints = strongs_hints_from_lemma(lemma)
            sig = (lemma, morph, tuple(hints))
            b = buckets[norm]
            if sig not in b:
                b[sig] = {
                    "lemma": lemma,
                    "morph": morph,
                    "strongs_hints": hints,
                }
            elem.clear()

    index: dict[str, list[dict[str, Any]]] = {}
    for norm, sigmap in buckets.items():
        index[norm] = sorted(sigmap.values(), key=lambda r: (r["lemma"], r["morph"]))
    stats["unique_norm_keys"] = len(index)
    return index, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Build morphhb WLC normalized-form index")
    ap.add_argument("--wlc-dir", type=Path, default=DEFAULT_WLC_DIR)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_INDEX_OUT)
    ap.add_argument(
        "--files",
        type=str,
        nargs="*",
        default=None,
        help="Explicit XML paths (default: all *.xml in wlc except VerseMap)",
    )
    args = ap.parse_args()

    wlc_dir = Path(args.wlc_dir)
    if not args.files:
        files = iter_wlc_book_xml_files(wlc_dir)
    else:
        files = [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.files]

    if not files:
        print(f"ERROR: no WLC XML files under {wlc_dir}", flush=True)
        return 2
    for p in files:
        if not p.is_file():
            print(f"ERROR: missing {p}", flush=True)
            return 2

    index, st = build_index(files)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload: dict[str, Any] = {
        "schema": "morphhb_norm_to_lemma_index_v1",
        "generated_at_utc": ts,
        "inputs": {
            "wlc_dir": str(wlc_dir.resolve()) if wlc_dir.is_dir() else str(wlc_dir),
            "xml_files": [str(p.resolve()) for p in files],
        },
        "stats": st,
        "index": index,
    }

    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"OK": True, "out": str(out), **st}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
