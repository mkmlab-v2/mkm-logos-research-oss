#!/usr/bin/env python3
"""Build B-track NT textual-variant distance layer (15 MT-only gaps) — never merges into complete JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_POLICY = ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl"
DEFAULT_CLASSIFY = ROOT / "docs/final/artifacts/logos_gap_mt_only_residual_classify_v1_latest.json"
DEFAULT_SINGLE = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
DEFAULT_SBLGNT = ROOT / "vault/external_lexicon/sources/morphgnt-sblgnt"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_textual_variant_distance_v1_latest.json"
DEFAULT_TR_VECTORS = ROOT / "docs/final/artifacts/logos_tr_variant_vectors_v1_latest.jsonl"
DEFAULT_TR_GREEK = ROOT / "data/logos/manuscripts/tr_greek_by_verse_v1.jsonl"
NEUTRAL_4D = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved.as_posix())


def _status_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entries:
        st = str((e.get("distance") or {}).get("primary_status") or (e.get("distance") or {}).get("status") or "unknown")
        counts[st] = counts.get(st, 0) + 1
    return counts


def _greek_preview(text: str, n: int = 80) -> str:
    t = text.strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _load_jsonl_index(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vid = str(row.get("verse_id") or "").strip()
        if vid:
            out[vid] = row
    return out


def _l2(a: dict[str, float], b: dict[str, float]) -> float:
    return sum((float(a[k]) - float(b[k])) ** 2 for k in ("S", "L", "K", "M")) ** 0.5


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(float(a[k]) * float(b[k]) for k in ("S", "L", "K", "M"))
    na = sum(float(a[k]) ** 2 for k in ("S", "L", "K", "M")) ** 0.5
    nb = sum(float(b[k]) ** 2 for k in ("S", "L", "K", "M")) ** 0.5
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


def _vec_from_row(row: dict[str, Any]) -> dict[str, float]:
    v = row.get("vector_4d") or row.get("unified_4d_vector") or NEUTRAL_4D
    if not isinstance(v, dict):
        v = NEUTRAL_4D
    return {k: float(v.get(k, 0.25)) for k in ("S", "L", "K", "M")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-jsonl", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--classify-json", type=Path, default=DEFAULT_CLASSIFY)
    ap.add_argument("--single-anchor-jsonl", type=Path, default=DEFAULT_SINGLE)
    ap.add_argument("--sblgnt-dir", type=Path, default=DEFAULT_SBLGNT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--tr-vectors-jsonl", type=Path, default=DEFAULT_TR_VECTORS)
    ap.add_argument("--tr-greek-jsonl", type=Path, default=DEFAULT_TR_GREEK)
    args = ap.parse_args()

    if not args.policy_jsonl.is_file():
        print(f"missing policy: {args.policy_jsonl}", file=sys.stderr)
        return 2

    classify_by_id: dict[str, dict[str, Any]] = {}
    if args.classify_json.is_file():
        doc = json.loads(args.classify_json.read_text(encoding="utf-8"))
        for row in doc.get("verses") or []:
            if isinstance(row, dict) and row.get("verse_id"):
                classify_by_id[str(row["verse_id"])] = row

    single = _load_jsonl_index(args.single_anchor_jsonl)
    tr_vec = _load_jsonl_index(args.tr_vectors_jsonl)
    tr_greek = _load_jsonl_index(args.tr_greek_jsonl)
    sblgnt_index: dict[str, str] = {}
    if args.sblgnt_dir.is_dir():
        from scripts.ingest_logos_gap_original_text_v1 import _build_sblgnt_index  # noqa: E402

        sblgnt_index = _build_sblgnt_index(args.sblgnt_dir)

    from scripts.logos_nt_adjacent_verse_v1 import (  # noqa: E402
        adjacent_mt_verse_ids,
        pick_sblgnt_filled_neighbor,
    )
    from scripts.logos_stepbible_versification_v1 import (  # noqa: E402
        load_stepbible_eng_to_greek,
        stepbible_sblgnt_candidates_for_mt_verse,
    )

    grk_map = load_stepbible_eng_to_greek()
    entries: list[dict[str, Any]] = []

    for line in args.policy_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pol = json.loads(line)
        vid = str(pol["verse_id"])
        cls = classify_by_id.get(vid, {})
        sa = single.get(vid, {})
        mt_vec = _vec_from_row(sa)
        sb_cands = stepbible_sblgnt_candidates_for_mt_verse(vid, greek_map=grk_map)
        sbl_present = bool(sblgnt_index.get(vid)) or any(
            sblgnt_index.get(c) for c in sb_cands
        )
        proxy_vec: dict[str, float] | None = None
        proxy_vid: str | None = None
        if sbl_present and sblgnt_index.get(vid):
            proxy_row = single.get(vid, {})
            if proxy_row:
                proxy_vec = _vec_from_row(proxy_row)
                proxy_vid = vid
        else:
            for c in sb_cands:
                if sblgnt_index.get(c) and c in single:
                    proxy_vec = _vec_from_row(single[c])
                    proxy_vid = c
                    break
        if proxy_vec is None:
            hit = pick_sblgnt_filled_neighbor(vid, single, span=2)
            if hit:
                proxy_vid, proxy_row = hit
                proxy_vec = _vec_from_row(proxy_row)
        dist_status = "pending_tr_source"
        dist_l2: float | None = None
        dist_cos: float | None = None
        dist_note = (
            "SBLGNT vector unavailable for this MT verse_id; "
            "TR/Byzantine Greek ingest is a separate B-track source — "
            "merge into verse_decoded_v2_complete forbidden."
        )
        adjacent_block: dict[str, Any] | None = None
        if proxy_vec is not None:
            used_adjacent = proxy_vid in adjacent_mt_verse_ids(vid, span=2)
            adj_status = "nt_adjacent_lexical_proxy" if used_adjacent else "sblgnt_neighbor_proxy"
            adjacent_block = {
                "status": adj_status,
                "l2_vector_4d": round(_l2(mt_vec, proxy_vec), 6),
                "cosine_vector_4d": round(_cosine(mt_vec, proxy_vec), 6),
                "proxy_verse_id": proxy_vid,
            }
            if dist_status == "pending_tr_source":
                dist_status = adj_status
                dist_l2 = adjacent_block["l2_vector_4d"]
                dist_cos = adjacent_block["cosine_vector_4d"]
                dist_note = (
                    f"Proxy: MT neutral stub vs lexical-filled verse_id={proxy_vid} "
                    f"({'same-chapter adjacent' if used_adjacent else 'STEPBible/SBLGNT index'}); "
                    "not TR textual distance."
                )

        tr_row = tr_vec.get(vid, {})
        tr_g = tr_greek.get(vid, {})
        tr_v = _vec_from_row(tr_row) if tr_row else None
        tr_block: dict[str, Any] | None = None
        tr_tradition: dict[str, Any] = {
            "source_id": "TR_placeholder_v1",
            "licensed": False,
            "greek_text": None,
            "greek_text_preview": None,
            "ingest_status": "pending_source",
        }
        if tr_g or tr_row:
            greek_full = str(tr_g.get("greek_text") or "")
            tr_tradition = {
                "source_id": str(
                    tr_g.get("source_id") or tr_row.get("source_id") or "TR_SCRIVENER_1894_HONZA"
                ),
                "licensed": True,
                "greek_text_preview": _greek_preview(greek_full) if greek_full else None,
                "ingest_status": "ingested",
                "license_tag": tr_g.get("license_tag"),
            }
        if tr_v is not None:
            tr_l2_stub = round(_l2(mt_vec, tr_v), 6)
            tr_cos_stub = round(_cosine(mt_vec, tr_v), 6)
            tr_l2_adj: float | None = None
            tr_cos_adj: float | None = None
            if proxy_vec is not None:
                tr_l2_adj = round(_l2(tr_v, proxy_vec), 6)
                tr_cos_adj = round(_cosine(tr_v, proxy_vec), 6)
            tr_block = {
                "l2_mt_stub_vs_tr": tr_l2_stub,
                "cosine_mt_stub_vs_tr": tr_cos_stub,
                "l2_tr_vs_adjacent_sblgnt_proxy": tr_l2_adj,
                "cosine_tr_vs_adjacent_sblgnt_proxy": tr_cos_adj,
            }
            dist_status = "tr_lexical_with_adjacent_proxy" if adjacent_block else "tr_lexical_present"
            dist_l2 = tr_l2_stub
            dist_cos = tr_cos_stub
            dist_note = (
                "TR Scrivener 1894 Greek via gematria_bridge_v1; "
                "SBLGNT same-verse absent — not merged into complete JSONL."
            )

        entry: dict[str, Any] = {
            "verse_id": vid,
            "testament": "NT",
            "residual_taxonomy": cls.get("residual_taxonomy") or "textual_variant_omission",
            "decode_status": pol.get("decode_status"),
            "sblgnt_local": {
                "present_in_morphgnt_index": sbl_present,
                "stepbible_sblgnt_candidates": sb_cands,
            },
            "tr_tradition": tr_tradition,
            "tr_vector_4d": tr_v,
            "mt_only_vector_4d": mt_vec,
            "distance": {
                "primary_status": dist_status,
                "status": dist_status,
                "l2_vector_4d": dist_l2,
                "cosine_vector_4d": dist_cos,
                "sblgnt_proxy_verse_id": proxy_vid,
                "tr_lexical": tr_block,
                "adjacent_proxy": adjacent_block,
                "note": dist_note,
            },
            "interpretation": pol.get("interpretation"),
        }
        entries.append(entry)

    entries.sort(key=lambda r: r["verse_id"])
    gap_count = len(entries)
    doc = {
        "schema": "logos_textual_variant_distance_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "source_track": "B_textual_criticism",
        "canonical_ssot": {
            "complete_jsonl": "data/logos/verse_decoded_v2_complete_v1.jsonl",
            "complete_gap_count": gap_count,
            "mt_only_policy_jsonl": _rel(args.policy_jsonl),
            "residual_classify_json": _rel(args.classify_json)
            if args.classify_json.is_file()
            else None,
        },
        "entries": entries,
        "aggregate": {
            "entry_count": gap_count,
            "distance_status_counts": _status_counts(entries),
            "mt_only_neutral_vector_count": sum(
                1
                for e in entries
                if _l2(e["mt_only_vector_4d"], NEUTRAL_4D) < 1e-9
            ),
        },
        "track_wall": {
            "merge_into_complete_jsonl": False,
            "a_track_auto_promotion": False,
            "ready_for_external_send": False,
            "forbidden_claim": "primary_bhs_sblgnt_decode_for_all_31102",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} entries={gap_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
