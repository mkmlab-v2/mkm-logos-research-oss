#!/usr/bin/env python3
"""Ingest BHS (morphhb WLC) and SBLGNT (morphgnt) original text for gap verses only.

Output rows match verse_decoded_v2 shape. Does not overwrite verse_decoded_v2.jsonl.
Track B / [HYPO] — not Track A promotion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_verse_gap_staging_v1 import (  # noqa: E402
    DEFAULT_DIFF,
    _gematria_fields,
)
from scripts.logos_mt_wlc_verse_map_v1 import mt_verse_id_to_wlc_osis_candidates  # noqa: E402
from scripts.logos_stepbible_versification_v1 import (  # noqa: E402
    DEFAULT_TVTMS,
    load_stepbible_eng_to_greek,
    stepbible_sblgnt_candidates_for_mt_verse,
)

DEFAULT_QUEUE = ROOT / "reports/constitution/btrack_pilot/logos_verse_gap_ingest_queue_v1_latest.jsonl"
DEFAULT_WLC_DIR = ROOT / "vault/external_lexicon/sources/openscriptures-morphhb/wlc"
DEFAULT_SBLGNT_DIR = ROOT / "vault/external_lexicon/sources/morphgnt-sblgnt"
DEFAULT_OUT = ROOT / "data/logos/verse_decoded_v2_lexical_fill_v1.jsonl"
DEFAULT_META = ROOT / "docs/final/artifacts/logos_verse_lexical_fill_v1_latest.json"

NT_BOOKS = frozenset(
    {
        "Matt",
        "Mark",
        "Luke",
        "John",
        "Jhn",
        "Acts",
        "Rom",
        "1Cor",
        "2Cor",
        "Gal",
        "Eph",
        "Phil",
        "Col",
        "1Thess",
        "2Thess",
        "1Tim",
        "2Tim",
        "Titus",
        "Phlm",
        "Heb",
        "Jas",
        "1Pet",
        "2Pet",
        "1John",
        "2John",
        "3John",
        "Jude",
        "Rev",
    }
)

MORPHGNT_SUFFIX_TO_BOOK: dict[str, str] = {
    "Mt": "Matt",
    "Mk": "Mark",
    "Lk": "Luke",
    "Jn": "Jhn",
    "Ac": "Acts",
    "Ro": "Rom",
    "1Co": "1Cor",
    "2Co": "2Cor",
    "Ga": "Gal",
    "Eph": "Eph",
    "Php": "Phil",
    "Col": "Col",
    "1Th": "1Thess",
    "2Th": "2Thess",
    "1Ti": "1Tim",
    "2Ti": "2Tim",
    "Tit": "Titus",
    "Phm": "Phlm",
    "Heb": "Heb",
    "Jas": "Jas",
    "1Pe": "1Pet",
    "2Pe": "2Pet",
    "1Jn": "1John",
    "2Jn": "2John",
    "3Jn": "3John",
    "Jud": "Jude",
    "Re": "Rev",
}

OSIS_NS = {"osis": "http://www.bibletechnologies.net/2003/OSIS/namespace"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _strip_greek_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _source_ref(verse_id: str) -> str:
    parts = verse_id.split(".")
    if len(parts) >= 3:
        return f"{parts[0]} {parts[1]}:{parts[2]}"
    return verse_id.replace(".", " ")


def _iter_queue(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            vid = str(obj.get("verse_id") or "").strip()
            if vid:
                yield vid


def _load_missing_ids(diff_path: Path) -> set[str]:
    diff = json.loads(diff_path.read_text(encoding="utf-8-sig"))
    missing = diff.get("missing_verse_ids")
    if not isinstance(missing, list):
        raise ValueError("coverage diff missing missing_verse_ids")
    return {str(v).strip() for v in missing if str(v).strip()}


def _wlc_book_path(wlc_dir: Path, book: str) -> Path:
    return wlc_dir / f"{book}.xml"


def _extract_wlc_verse_text(xml_path: Path, osis_id: str) -> str | None:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    xpath = f".//osis:verse[@osisID='{osis_id}']"
    verse_el = root.find(xpath, OSIS_NS)
    if verse_el is None:
        return None
    parts: list[str] = []
    for w in verse_el.findall("osis:w", OSIS_NS):
        if w.text:
            parts.append(w.text.strip())
        if w.tail:
            parts.append(w.tail.strip())
    text = " ".join(p for p in parts if p)
    return text.strip() or None


def _build_wlc_index(wlc_dir: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    for xml_path in sorted(wlc_dir.glob("*.xml")):
        book = xml_path.stem
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        for verse_el in root.findall(".//osis:verse", OSIS_NS):
            osis_id = verse_el.get("osisID")
            if not osis_id or not osis_id.startswith(f"{book}."):
                continue
            parts: list[str] = []
            for w in verse_el.findall("osis:w", OSIS_NS):
                if w.text:
                    parts.append(w.text.strip())
                if w.tail:
                    parts.append(w.tail.strip())
            text = " ".join(p for p in parts if p).strip()
            if text:
                index[osis_id] = text
    return index


def _morphgnt_book_num_map(sblgnt_dir: Path) -> dict[str, str]:
    """Map morphgnt BB (2-digit book) -> canon book id (Matt, Mark, …)."""
    out: dict[str, str] = {}
    for path in sorted(sblgnt_dir.glob("*-morphgnt.txt")):
        stem = path.name.split("-", 1)[1].replace("-morphgnt.txt", "")
        canon = MORPHGNT_SUFFIX_TO_BOOK.get(stem)
        if not canon:
            continue
        with path.open("r", encoding="utf-8") as f:
            first = f.readline().strip()
        if not first:
            continue
        ref = first.split()[0]
        if len(ref) >= 2:
            out[ref[:2]] = canon
    return out


def _build_sblgnt_index(sblgnt_dir: Path) -> dict[str, str]:
    book_num = _morphgnt_book_num_map(sblgnt_dir)
    index: dict[str, str] = {}
    current_key: str | None = None
    tokens: list[str] = []

    def flush() -> None:
        nonlocal current_key, tokens
        if current_key and tokens:
            index[current_key] = " ".join(tokens)
        current_key = None
        tokens = []

    for path in sorted(sblgnt_dir.glob("*-morphgnt.txt")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                fields = line.split()
                if len(fields) < 4:
                    continue
                ref = fields[0]
                if len(ref) != 6 or not ref.isdigit():
                    continue
                bb, cc, vv = ref[:2], ref[2:4], ref[4:6]
                book = book_num.get(bb)
                if not book:
                    continue
                verse_key = f"{book}.{int(cc)}.{int(vv)}"
                surface = fields[3]
                surface = re.sub(r"^[⸀⸂⸃]+", "", surface)
                if verse_key != current_key:
                    flush()
                    current_key = verse_key
                tokens.append(surface)
        flush()
    return index


def _bhs_row(verse_id: str, original_text: str, *, ts: str) -> dict[str, Any]:
    g = _gematria_fields(original_text)
    return {
        "verse_id": verse_id,
        "source_ref": _source_ref(verse_id),
        "edition": "BHS",
        "text": original_text.replace("/", " ").replace("  ", " ").strip(),
        "original_text": original_text,
        "hebrew_value": g["hebrew_value"],
        "greek_value": 0,
        "ascii_value": g["ascii_value"],
        "total_value": g["total_value"],
        "normalized_value": g["normalized_value"],
        "interpretation": f"게마트리아 값 {g['total_value']} (morphhb WLC ingest, B-track)",
        "vector_4d": g["vector_4d"],
        "physical_constants_match": g["physical_constants_match"],
        "unified_4d_vector": g["unified_4d_vector"],
        "lambda_entropy": 0.0,
        "distance_to_centroid": None,
        "phase_phi": None,
        "s_hash": verse_id,
        "c_mass_index": None,
        "timestamp": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "decode_status": "morphhb_wlc_v1",
        "lexical_source": "openscriptures-morphhb/wlc",
        "upstream_original_text_missing": False,
    }


def _sblgnt_row(verse_id: str, original_text: str, *, ts: str) -> dict[str, Any]:
    g = _gematria_fields(original_text)
    plain = _strip_greek_accents(original_text).lower()
    return {
        "verse_id": verse_id,
        "source_ref": _source_ref(verse_id),
        "edition": "SBLGNT",
        "text": plain,
        "original_text": original_text,
        "hebrew_value": 0,
        "greek_value": g["greek_value"],
        "ascii_value": g["ascii_value"],
        "total_value": g["total_value"],
        "normalized_value": g["normalized_value"],
        "interpretation": f"게마트리아 값 {g['total_value']} (morphgnt SBLGNT ingest, B-track)",
        "vector_4d": g["vector_4d"],
        "physical_constants_match": g["physical_constants_match"],
        "unified_4d_vector": g["unified_4d_vector"],
        "lambda_entropy": 0.0,
        "distance_to_centroid": None,
        "phase_phi": None,
        "s_hash": verse_id,
        "c_mass_index": None,
        "timestamp": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "decode_status": "morphgnt_sblgnt_v1",
        "lexical_source": "morphgnt/sblgnt",
        "upstream_original_text_missing": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gap-queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--coverage-diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--wlc-dir", type=Path, default=DEFAULT_WLC_DIR)
    ap.add_argument("--sblgnt-dir", type=Path, default=DEFAULT_SBLGNT_DIR)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-meta", type=Path, default=DEFAULT_META)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all gap verses")
    ap.add_argument("--skip-wlc", action="store_true")
    ap.add_argument("--skip-sblgnt", action="store_true")
    args = ap.parse_args()

    if not args.gap_queue.is_file():
        print(f"missing gap queue: {args.gap_queue}", file=sys.stderr)
        return 2

    want = _load_missing_ids(args.coverage_diff)
    queue_ids = list(_iter_queue(args.gap_queue))
    targets = [v for v in queue_ids if v in want]
    if args.max_rows > 0:
        targets = targets[: args.max_rows]

    ts = _utc_now()
    wlc_index: dict[str, str] = {}
    sblgnt_index: dict[str, str] = {}
    if not args.skip_wlc:
        if not args.wlc_dir.is_dir():
            print(f"missing WLC dir: {args.wlc_dir}", file=sys.stderr)
            return 2
        print("indexing morphhb WLC …", flush=True)
        wlc_index = _build_wlc_index(args.wlc_dir)
        print(f"  wlc verses indexed: {len(wlc_index)}", flush=True)
    if not args.skip_sblgnt:
        if not args.sblgnt_dir.is_dir():
            print(f"missing SBLGNT dir: {args.sblgnt_dir}", file=sys.stderr)
            return 2
        print("indexing morphgnt SBLGNT …", flush=True)
        sblgnt_index = _build_sblgnt_index(args.sblgnt_dir)
        print(f"  sblgnt verses indexed: {len(sblgnt_index)}", flush=True)

    filled_bhs = 0
    filled_sbl = 0
    filled_bhs_stepbible = 0
    filled_sbl_stepbible = 0
    missing_ot = 0
    missing_nt = 0
    missing_ot_verse_ids: list[str] = []
    missing_nt_verse_ids: list[str] = []
    stepbible_greek = load_stepbible_eng_to_greek()

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as out:
        for vid in targets:
            book = vid.split(".")[0]
            is_nt = book in NT_BOOKS
            if is_nt:
                text = sblgnt_index.get(vid)
                via = "direct"
                alt = None
                if not text:
                    for alt in stepbible_sblgnt_candidates_for_mt_verse(
                        vid, greek_map=stepbible_greek
                    ):
                        text = sblgnt_index.get(alt)
                        if text:
                            via = "stepbible_versification"
                            break
                if text:
                    row = _sblgnt_row(vid, text, ts=ts)
                    row["lexical_source"] = (
                        "morphgnt/sblgnt"
                        if via == "direct"
                        else "morphgnt/sblgnt+stepbible_versification"
                    )
                    if via == "stepbible_versification":
                        row["stepbible_sblgnt_verse_id"] = alt
                        filled_sbl_stepbible += 1
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    filled_sbl += 1
                else:
                    missing_nt += 1
                    missing_nt_verse_ids.append(vid)
            else:
                text = None
                for cand in mt_verse_id_to_wlc_osis_candidates(vid):
                    text = wlc_index.get(cand)
                    if text:
                        break
                if text:
                    row = _bhs_row(vid, text, ts=ts)
                    if vid not in wlc_index and any(
                        c != vid for c in mt_verse_id_to_wlc_osis_candidates(vid)
                    ):
                        row["lexical_source"] = "openscriptures-morphhb/wlc+stepbible_versification"
                        filled_bhs_stepbible += 1
                    out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    filled_bhs += 1
                else:
                    missing_ot += 1
                    missing_ot_verse_ids.append(vid)

    meta = {
        "schema": "logos_verse_lexical_fill_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "targets": len(targets),
        "filled_bhs": filled_bhs,
        "filled_bhs_via_stepbible": filled_bhs_stepbible,
        "filled_sblgnt": filled_sbl,
        "filled_sblgnt_via_stepbible": filled_sbl_stepbible,
        "stepbible_tvtms_present": DEFAULT_TVTMS.is_file(),
        "filled_total": filled_bhs + filled_sbl,
        "missing_ot": missing_ot,
        "missing_nt": missing_nt,
        "missing_ot_verse_ids": missing_ot_verse_ids,
        "missing_nt_verse_ids": missing_nt_verse_ids,
        "still_gap": len(targets) - filled_bhs - filled_sbl,
        "wlc_index_size": len(wlc_index),
        "sblgnt_index_size": len(sblgnt_index),
        "out_jsonl": _rel(args.out_jsonl),
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
        "note": (
            "Lexical fill from local vault sources only. "
            "MT-only verses absent from WLC/SBLGNT remain unfilled."
        ),
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out_jsonl} filled={filled_bhs + filled_sbl} "
        f"bhs={filled_bhs} sblgnt={filled_sbl} missing_ot={missing_ot} missing_nt={missing_nt}",
        flush=True,
    )
    return 0 if (filled_bhs + filled_sbl) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
