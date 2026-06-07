#!/usr/bin/env python3
"""Ingest ETCBC DSS corpus → metadata-only token NDJSON (no scroll surface text).

Supports:
  - text-fabric ETCBC/dss v1.9 when ``--tf-loc`` or default cache is available
  - offline scroll manifest (``dss_pilot_scrolls.json``) for research rebuild

research_only · [HYPO] · not Track A.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "text",
        "token_text",
        "surface",
        "lemma",
        "gloss",
        "word",
        "full",
        "fulle",
        "fullo",
        "glyph",
        "glyphe",
        "glypho",
        "lex",
        "lexe",
        "lexo",
        "glex",
        "glexe",
        "glexo",
    }
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            clean = {k: v for k, v in row.items() if k not in FORBIDDEN_OUTPUT_KEYS}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")


def _tokens_from_scroll_manifest(
    manifest: dict[str, Any],
    *,
    feature_map: dict[str, Any],
    max_tokens: int,
    dataset_version: str,
) -> list[dict[str, Any]]:
    defaults = feature_map.get("defaults") or {}
    rows: list[dict[str, Any]] = []
    scrolls = manifest.get("scrolls") or []
    for scroll in scrolls:
        if not isinstance(scroll, dict):
            continue
        budget = int(scroll.get("tokens_budget") or 0)
        scroll_id = str(scroll.get("scroll_id") or scroll.get("work") or "unknown")
        work = str(scroll.get("work") or scroll_id)
        book = str(scroll.get("book") or "")
        mt_hint = str(scroll.get("mt_ref_hint") or "")
        for idx in range(1, budget + 1):
            if len(rows) >= max_tokens:
                return rows
            rows.append(
                {
                    "work": work,
                    "token_index": idx,
                    "script": defaults.get("script", "hebrew"),
                    "lineage_tier": defaults.get("lineage_tier", "A_HEBREW_PRIMARY"),
                    "source": defaults.get("source", "ETCBC_DSS"),
                    "lang": defaults.get("lang", "he"),
                    "scroll_id": scroll_id,
                    "book": book,
                    "tf_slot": f"{scroll_id}.{idx}",
                    "mt_ref": mt_hint,
                    "dataset_version": dataset_version,
                    "alignment_delta": 0,
                }
            )
    return rows[:max_tokens]


def _corpus_ready(tf_loc: Path) -> bool:
    return tf_loc.is_dir() and any(tf_loc.glob("*.tf"))


def _scroll_catalog_entries(scrolls_json: Path) -> list[dict[str, Any]]:
    if not scrolls_json.is_file():
        return []
    doc = _load_json(scrolls_json)
    scrolls = [s for s in doc.get("scrolls") or [] if isinstance(s, dict)]
    bridge = [s for s in scrolls if s.get("fusion_bridge")]
    other = [s for s in scrolls if not s.get("fusion_bridge")]
    return bridge + other


def _try_textfabric_tokens(
    *,
    tf_loc: Path,
    scrolls_json: Path,
    max_tokens: int,
    dataset_version: str,
) -> list[dict[str, Any]] | None:
    if not _corpus_ready(tf_loc):
        return None
    try:
        from tf.app import use  # type: ignore
    except ImportError:
        return None

    try:
        A = use("ETCBC/dss", checkout="clone", version="1.9", silent=True)
        A.load("", silent=True)
        F = A.api.F
        L = A.api.L
    except Exception:
        return None

    catalog = _scroll_catalog_entries(scrolls_json)
    scroll_work_map = {
        str(s.get("scroll_id") or ""): str(s.get("work") or s.get("scroll_id") or "")
        for s in catalog
        if s.get("scroll_id")
    }

    rows: list[dict[str, Any]] = []
    per_work: dict[str, int] = {}
    book_bridge = {"Sir": "Ben_Sira", "Jub": "Jubilees", "Eno": "1_Enoch", "Num": "Numbers"}

    try:
        words = list(F.otype.s("word"))
    except Exception:
        return None

    by_scroll: dict[str, list[Any]] = {}
    for w in words:
        try:
            scroll_node = L.u(w, otype="scroll")[0]
            scroll_id = str(F.scroll.v(scroll_node) or "unknown")
        except Exception:
            scroll_id = "unknown"
        by_scroll.setdefault(scroll_id, []).append(w)

    def _append_word(w: Any, scroll_id: str) -> None:
        if len(rows) >= max_tokens:
            return
        book = str(F.book.v(w) or "")
        work = scroll_work_map.get(scroll_id) or book_bridge.get(book, scroll_id)
        per_work[work] = per_work.get(work, 0) + 1
        script_val = str(F.script.v(w) or "hebrew")
        lang_val = str(F.lang.v(w) or "he")
        lineage = "A_HEBREW_PRIMARY" if script_val == "hebrew" or lang_val == "he" else "C_TRANSLATION_PROXY"
        rows.append(
            {
                "work": work,
                "token_index": per_work[work],
                "script": script_val if script_val else "hebrew",
                "lineage_tier": lineage,
                "source": "ETCBC_DSS",
                "lang": lang_val,
                "scroll_id": scroll_id,
                "book": book,
                "fragment": str(F.fragment.v(w) or ""),
                "line": str(F.line.v(w) or ""),
                "tf_slot": str(F.srcLn.v(w) or w),
                "dataset_version": dataset_version,
                "alignment_delta": 0,
            }
        )

    taken_per_scroll: dict[str, int] = {}

    def _take_from_scroll(scroll_id: str, take: int) -> None:
        if take <= 0 or scroll_id not in by_scroll:
            return
        start = taken_per_scroll.get(scroll_id, 0)
        for w in by_scroll[scroll_id][start : start + take]:
            _append_word(w, scroll_id)
        taken_per_scroll[scroll_id] = start + take

    for scroll in catalog:
        if len(rows) >= max_tokens:
            break
        scroll_id = str(scroll.get("scroll_id") or "")
        budget = int(scroll.get("tokens_budget") or 0)
        if budget <= 0:
            continue
        take = min(budget, max_tokens - len(rows))
        _take_from_scroll(scroll_id, take)

    if len(rows) < max_tokens:
        for scroll in catalog:
            if len(rows) >= max_tokens:
                break
            scroll_id = str(scroll.get("scroll_id") or "")
            need = max_tokens - len(rows)
            _take_from_scroll(scroll_id, need)

    bridge_works = {
        str(s.get("work") or s.get("scroll_id") or "").strip()
        for s in catalog
        if s.get("fusion_bridge") and (s.get("work") or s.get("scroll_id"))
    }
    present_works = {str(r.get("work") or "") for r in rows}
    missing_bridge = sorted(w for w in bridge_works if w and w not in present_works)
    if missing_bridge:
        manifest = _load_json(scrolls_json)
        fm_path = scrolls_json.parent / "tf_feature_map.default.json"
        fm = _load_json(fm_path) if fm_path.is_file() else {"defaults": {}}
        supplement = _tokens_from_scroll_manifest(
            manifest,
            feature_map=fm,
            max_tokens=max_tokens,
            dataset_version=dataset_version,
        )
        bridge_rows = [r for r in supplement if str(r.get("work") or "") in missing_bridge]
        if bridge_rows:
            rows = (rows + bridge_rows)[:max_tokens]
    return rows if rows else None


def main() -> int:
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tf-loc", type=Path, default=root.parent.parent / "data" / "etcbc-dss" / "tf" / "1.9")
    ap.add_argument("--scrolls-json", type=Path, default=root / "dss_pilot_scrolls.json")
    ap.add_argument("--tf-feature-map", type=Path, default=root / "tf_feature_map.default.json")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--dataset-version", default="dss-pilot-tf4")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--force-manifest", action="store_true", help="Skip text-fabric; use scroll manifest only.")
    args = ap.parse_args()

    feature_map = _load_json(args.tf_feature_map) if args.tf_feature_map.is_file() else {}
    rows: list[dict[str, Any]] | None = None

    if not args.force_manifest:
        rows = _try_textfabric_tokens(
            tf_loc=args.tf_loc,
            scrolls_json=args.scrolls_json,
            max_tokens=args.max_tokens,
            dataset_version=args.dataset_version,
        )

    ingest_mode = "textfabric"
    if not rows:
        if not args.scrolls_json.is_file():
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"missing scroll manifest: {args.scrolls_json}",
                        "hint": "run setup_etcbc_dss_data_v1.py or pass --scrolls-json",
                    }
                ),
                file=sys.stderr,
            )
            return 2
        manifest = _load_json(args.scrolls_json)
        rows = _tokens_from_scroll_manifest(
            manifest,
            feature_map=feature_map,
            max_tokens=args.max_tokens,
            dataset_version=args.dataset_version,
        )
        ingest_mode = "scroll_manifest"

    if not rows:
        print(json.dumps({"ok": False, "error": "no token rows produced"}), file=sys.stderr)
        return 2

    _write_ndjson(args.out, rows)
    print(f"wrote {len(rows)} records to {args.out}")
    print(
        json.dumps(
            {
                "ok": True,
                "records": len(rows),
                "ingest_mode": ingest_mode,
                "out": str(args.out),
                "research_only": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
