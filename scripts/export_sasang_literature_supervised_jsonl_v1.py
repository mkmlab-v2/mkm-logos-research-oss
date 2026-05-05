#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export text + label JSONL from resolved joint rows (literature-only supervised slice).

Each line: ``schema``, ``text`` (title + abstract), ``label_en``, ``label_ko``, ``pmid``, ``tier``.
Skips rows without ``sasang_constitution``. Does not include birth / saju pillars.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_auto_resolved_v1.jsonl"
DEFAULT_CATALOG = ROOT / "data" / "myeongni" / "sasang_saju_literature_catalog_strict_high_signal_v1.jsonl"
DEFAULT_OUT = ROOT / "data" / "myeongni" / "sasang_literature_supervised_v1.jsonl"


def _catalog_map(path: Path) -> dict[str, dict[str, Any]]:
    m: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return m
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if str(r.get("schema") or "") != "sasang_saju_literature_catalog_row_v1":
            continue
        pid = str(r.get("pmid") or "").strip()
        if pid:
            m[pid] = r
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.inp.is_file():
        print(f"Missing --in {args.inp}", file=sys.stderr)
        return 2

    cat = _catalog_map(args.catalog)
    n = 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as outf:
        for line in args.inp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("schema") or "") != "sasang_saju_joint_benchmark_row_v1":
                continue
            sc = row.get("sasang_constitution")
            if not isinstance(sc, dict):
                continue
            en = str(sc.get("label_en") or "").strip()
            ko = str(sc.get("label_ko") or "").strip()
            if not en and not ko:
                continue
            pmids = row.get("literature_catalog_pmids") or []
            pmid = str(pmids[0] if pmids else "").strip()
            title = str((row.get("literature_catalog_snapshot") or {}).get("title") or row.get("display_name") or "")
            abstract = str(cat.get(pmid, {}).get("abstractText") or "")
            text = (title + "\n\n" + abstract).strip()
            if len(text) > 8000:
                text = text[:7997] + "..."
            doc = {
                "schema": "sasang_literature_supervised_row_v1",
                "text": text,
                "label_en": en or None,
                "label_ko": ko or None,
                "pmid": pmid or None,
                "tier": str(row.get("benchmark_tier") or ""),
            }
            outf.write(json.dumps(doc, ensure_ascii=False) + "\n")
            n += 1

    print(json.dumps({"wrote": n, "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
