#!/usr/bin/env python3
"""Classify remaining gap verses (no BHS/SBLGNT lexical fill) with honest MT-only policy labels."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ingest_logos_gap_original_text_v1 import (  # noqa: E402
    DEFAULT_DIFF,
    DEFAULT_QUEUE,
    NT_BOOKS,
    _build_sblgnt_index,
    _build_wlc_index,
    _iter_queue,
    _load_missing_ids,
)
from scripts.logos_mt_wlc_verse_map_v1 import mt_verse_id_to_wlc_osis_candidates  # noqa: E402

DEFAULT_FILL = ROOT / "data/logos/verse_decoded_v2_lexical_fill_v1.jsonl"
DEFAULT_OUT_JSONL = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_OUT_META = ROOT / "docs/final/artifacts/logos_gap_mt_only_policy_registry_v1_latest.json"
DEFAULT_WLC = ROOT / "vault/external_lexicon/sources/openscriptures-morphhb/wlc"
DEFAULT_SBLGNT = ROOT / "vault/external_lexicon/sources/morphgnt-sblgnt"

OSIS_NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
DECODE_STATUS = "mt_canon_only_no_critical_text"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _filled_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.add(str(json.loads(line).get("verse_id") or "").strip())
    return {v for v in out if v}


def _wlc_chapter_max_verse(wlc_dir: Path, book: str, ch: int) -> int:
    xml = wlc_dir / f"{book}.xml"
    if not xml.is_file():
        return -1
    root = ET.parse(xml).getroot()
    return len(root.findall(f".//o:chapter[@osisID='{book}.{ch}']/o:verse", OSIS_NS))


def _classify_stub(
    vid: str,
    *,
    wlc_index: dict[str, str],
    sblgnt_index: dict[str, str],
    wlc_dir: Path,
) -> dict[str, Any]:
    book = vid.split(".")[0]
    is_nt = book in NT_BOOKS
    testament = "NT" if is_nt else "OT"
    if is_nt:
        policy_class = "mt_canon_only_no_sblgnt"
        if sblgnt_index.get(vid):
            residual = "unexpected_sblgnt_present"
        else:
            residual = "sblgnt_absent_textual_variant_or_omission"
        stepbible_note = "NT: STEPBible versification typically OT-focused; no mapping attempted"
    else:
        policy_class = "mt_canon_only_no_wlc"
        wlc_hit = any(c in wlc_index for c in mt_verse_id_to_wlc_osis_candidates(vid))
        if wlc_hit:
            residual = "versification_rule_gap_despite_wlc_hit"
        else:
            parts = vid.split(".")
            ch, v = int(parts[1]), int(parts[2])
            wlc_max = _wlc_chapter_max_verse(wlc_dir, book, ch)
            if wlc_max >= 0 and v > wlc_max:
                residual = "mt_verse_beyond_wlc_chapter_end"
            else:
                residual = "wlc_versification_unmapped"
        stepbible_note = "OT: optional STEPBible Versification TSV when vault/stepbible-data present"
    return {
        "verse_id": vid,
        "testament": testament,
        "policy_class": policy_class,
        "decode_status": DECODE_STATUS,
        "residual_cause": residual,
        "upstream_original_text_missing": True,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "interpretation": (
            "[HYPO] MT canon SSOT verse without primary BHS/SBLGNT lexical source in local vault — "
            "pipeline vector/gematria stub only; not critical-text decode."
        ),
        "stepbible_versification_note": stepbible_note,
        "forbidden_claim": "primary_bhs_sblgnt_decode",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--gap-queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--lexical-fill-jsonl", type=Path, default=DEFAULT_FILL)
    ap.add_argument("--wlc-dir", type=Path, default=DEFAULT_WLC)
    ap.add_argument("--sblgnt-dir", type=Path, default=DEFAULT_SBLGNT)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_OUT_META)
    args = ap.parse_args()

    want = _load_missing_ids(args.coverage_diff)
    filled = _filled_ids(args.lexical_fill_jsonl)
    stubs = [
        v
        for v in _iter_queue(args.gap_queue)
        if v in want and v not in filled
    ]
    if not stubs:
        print("no stub verses to classify", file=sys.stderr)
        return 2

    wlc_index = _build_wlc_index(args.wlc_dir) if args.wlc_dir.is_dir() else {}
    sblgnt_index = _build_sblgnt_index(args.sblgnt_dir) if args.sblgnt_dir.is_dir() else {}

    ts = _utc_now()
    by_class: Counter[str] = Counter()
    by_testament: Counter[str] = Counter()
    by_residual: Counter[str] = Counter()

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as out:
        for vid in stubs:
            row = _classify_stub(
                vid,
                wlc_index=wlc_index,
                sblgnt_index=sblgnt_index,
                wlc_dir=args.wlc_dir,
            )
            by_class[row["policy_class"]] += 1
            by_testament[row["testament"]] += 1
            by_residual[row["residual_cause"]] += 1
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "schema": "logos_gap_mt_only_policy_registry_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "stub_count": len(stubs),
        "decode_status_unified": DECODE_STATUS,
        "by_testament": dict(by_testament),
        "by_policy_class": dict(by_class),
        "by_residual_cause": dict(by_residual),
        "out_jsonl": _rel(args.out_jsonl),
        "stepbible_data_present": (
            ROOT / "vault/external_lexicon/sources/stepbible-data"
        ).is_dir(),
        "next_optional": "scripts/fetch_stepbible_versification_v1.ps1 then ingest extension",
        "track_wall": {"ready_for_external_send": False, "a_track_auto_promotion": False},
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out_jsonl} stubs={len(stubs)} "
        f"nt={by_testament.get('NT', 0)} ot={by_testament.get('OT', 0)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
