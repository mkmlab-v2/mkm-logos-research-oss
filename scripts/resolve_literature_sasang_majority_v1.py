#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Second-pass resolver: majority vote on multi-type Sasang mentions; HTML-strip retry for no_match.

Reads ``sasang_saju_joint_benchmark_auto_v1.jsonl``, writes ``sasang_saju_joint_benchmark_auto_resolved_v1.jsonl``.
Does not set ``birth_resolution``.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_auto_v1.jsonl"
DEFAULT_OUT = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_auto_resolved_v1.jsonl"
DEFAULT_CATALOG = ROOT / "data" / "myeongni" / "sasang_saju_literature_catalog_strict_high_signal_v1.jsonl"

_TAG_RE = re.compile(r"<[^>]+>")
_ae_mod: Any = None


def _ae():
    global _ae_mod
    if _ae_mod is None:
        path = ROOT / "scripts" / "auto_enrich_sasang_from_literature_stub_v1.py"
        spec = importlib.util.spec_from_file_location("_ae_sasang", path)
        assert spec and spec.loader
        _ae_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ae_mod)
    return _ae_mod


def _strip_tags(s: str) -> str:
    t = _TAG_RE.sub(" ", s)
    return html.unescape(t)


def _load_catalog_by_pmid(path: Path) -> dict[str, dict[str, Any]]:
    return _ae()._load_catalog_by_pmid(path)  # type: ignore[attr-defined]


def _text_blob(stub: dict[str, Any], cat: dict[str, dict[str, Any]], *, strip_html: bool) -> str:
    b = _ae()._blob_for_stub(stub, cat)  # type: ignore[attr-defined]
    return _strip_tags(b) if strip_html else b


def _hits(blob: str) -> list[dict[str, Any]]:
    return _ae()._find_type_hits(blob)  # type: ignore[attr-defined]


def _quote_window(blob: str, start: int, end: int, *, width: int = 90) -> str:
    return _ae()._quote_window(blob, start, end, width=width)  # type: ignore[attr-defined]


def _majority_pick(
    hits: list[dict[str, Any]],
    *,
    ratio: float,
    margin: int,
    min_hits_for_ratio: int,
) -> tuple[str, str, dict[str, int]] | None:
    if not hits:
        return None
    cnt = Counter(h["label_en"] for h in hits)
    total = sum(cnt.values())
    (best_en, n_best) = cnt.most_common(1)[0]
    second = cnt.most_common(2)[1][1] if len(cnt.most_common(2)) > 1 else 0
    if n_best >= second + margin:
        pass_ok = True
    elif total > 0 and n_best / total >= ratio and n_best >= min_hits_for_ratio:
        pass_ok = True
    else:
        pass_ok = False
    if not pass_ok:
        return None
    ko = next(h["label_ko"] for h in hits if h["label_en"] == best_en)
    return best_en, ko, dict(cnt)


def _apply_hits(
    out: dict[str, Any],
    ext: dict[str, Any],
    blob: str,
    pmid: str,
    *,
    method: str,
    majority_ratio: float,
    majority_margin: int,
    majority_min_hits: int,
) -> bool:
    hits = _hits(blob)
    uniq = {(h["label_en"], h["label_ko"]) for h in hits}

    pick = _majority_pick(
        hits,
        ratio=majority_ratio,
        margin=majority_margin,
        min_hits_for_ratio=majority_min_hits,
    )
    if pick is not None:
        en, ko, counts = pick
        h0 = next(h for h in hits if h["label_en"] == en)
        out["sasang_constitution"] = {
            "label_en": en,
            "label_ko": ko,
            "confidence": 0.45,
            "source": {
                "pmid": pmid,
                "quote": _quote_window(blob, h0["start"], h0["end"]),
                "method": method,
                "majority_counts": counts,
            },
        }
        out["benchmark_tier"] = "auto_literature_sasang_majority_v1"
        ext.clear()
        ext.update(
            {
                "schema": "literature_sasang_extract_v1",
                "hit_count": len(hits),
                "distinct_types": len(uniq),
                "state": "resolved_majority_v1",
                "majority_counts": counts,
            }
        )
        return True

    if len(uniq) == 1 and hits:
        en, ko = next(iter(uniq))
        h0 = hits[0]
        out["sasang_constitution"] = {
            "label_en": en,
            "label_ko": ko,
            "confidence": 0.52,
            "source": {
                "pmid": pmid,
                "quote": _quote_window(blob, h0["start"], h0["end"]),
                "method": method,
            },
        }
        out["benchmark_tier"] = "auto_literature_sasang_only"
        ext.clear()
        ext.update(
            {
                "schema": "literature_sasang_extract_v1",
                "hit_count": len(hits),
                "distinct_types": 1,
                "state": "single_type",
            }
        )
        return True

    ext["hit_count"] = len(hits)
    ext["distinct_types"] = len(uniq)
    return False


def resolve_row(
    row: dict[str, Any],
    cat: dict[str, dict[str, Any]],
    *,
    majority_ratio: float,
    majority_margin: int,
    majority_min_hits: int,
) -> dict[str, Any]:
    out = dict(row)
    ext = dict(out.get("literature_sasang_extract") or {})
    pmids = out.get("literature_catalog_pmids") or []
    pmid = str(pmids[0] if pmids else "").strip()
    state = str(ext.get("state") or "")

    if state == "ambiguous_multi_type":
        blob = _text_blob(out, cat, strip_html=False)
        if _apply_hits(
            out,
            ext,
            blob,
            pmid,
            method="majority_vote_v1",
            majority_ratio=majority_ratio,
            majority_margin=majority_margin,
            majority_min_hits=majority_min_hits,
        ):
            out["literature_sasang_extract"] = ext
            out["provenance"] = (
                str(out.get("provenance") or "") + " | resolve_literature_sasang_majority_v1.py"
            ).strip()
            return out

    if state == "no_match":
        blob = _text_blob(out, cat, strip_html=True)
        if _apply_hits(
            out,
            ext,
            blob,
            pmid,
            method="regex_retry_htmlstrip_v1",
            majority_ratio=majority_ratio,
            majority_margin=majority_margin,
            majority_min_hits=majority_min_hits,
        ):
            out["literature_sasang_extract"] = ext
            out["provenance"] = (
                str(out.get("provenance") or "") + " | resolve_literature_sasang_majority_v1.py(html_strip)"
            ).strip()
            return out

    out["literature_sasang_extract"] = ext
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument(
        "--majority-ratio",
        type=float,
        default=0.55,
        help="Min share of hits for winning label (when margin rule fails)",
    )
    ap.add_argument(
        "--majority-margin",
        type=int,
        default=2,
        help="Win if best_count >= second_best + this margin",
    )
    ap.add_argument(
        "--majority-min-hits",
        type=int,
        default=2,
        help="Min raw hits for ratio rule to apply",
    )
    args = ap.parse_args()

    if not args.inp.is_file():
        print(f"Missing --in {args.inp}", file=sys.stderr)
        return 2

    cat = _load_catalog_by_pmid(args.catalog)
    stats = {
        "rows": 0,
        "resolved_majority": 0,
        "resolved_htmlstrip": 0,
        "unchanged": 0,
    }

    out_rows: list[dict[str, Any]] = []
    for line in args.inp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if str(row.get("schema") or "") != "sasang_saju_joint_benchmark_row_v1":
            continue
        before_state = (row.get("literature_sasang_extract") or {}).get("state")
        before_sasang = row.get("sasang_constitution")
        resolved = resolve_row(
            row,
            cat,
            majority_ratio=float(args.majority_ratio),
            majority_margin=int(args.majority_margin),
            majority_min_hits=int(args.majority_min_hits),
        )
        after_state = (resolved.get("literature_sasang_extract") or {}).get("state")
        after_sasang = resolved.get("sasang_constitution")
        stats["rows"] += 1
        changed = before_state != after_state or before_sasang != after_sasang
        if not changed:
            stats["unchanged"] += 1
        elif after_state == "resolved_majority_v1":
            stats["resolved_majority"] += 1
        elif before_state == "no_match" and after_state == "single_type":
            stats["resolved_htmlstrip"] += 1
        out_rows.append(resolved)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    sm = args.out.with_name(args.out.stem + "_summary_v1.json")
    sm.write_text(json.dumps({"schema": "resolve_literature_sasang_majority_summary_v1", "stats": stats}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "summary": str(sm), "stats": stats}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
