#!/usr/bin/env python3
"""Phase 1 lite — patient_care_bundle snippets · lexicon hit smoke ([HYPO])."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.master_codebook_lexicon_v1_bridge import lexicon_hits_for_text  # noqa: E402

PILOT = ROOT / "reports/constitution/btrack_pilot"
P41687 = PILOT / "master_codebook_lexicon_v1_41687_rows_latest.json"
P41708 = PILOT / "master_codebook_lexicon_v1_41708_rows_latest.json"
V2_LEXICON_SIGNOFF = ROOT / "docs/final/artifacts/hangul_curated_v2_track_a_lexicon_promotion_signoff_v1_latest.json"
OUT = ROOT / "reports/hangul_curated_clinical_snippet_lexicon_smoke_v1_latest.json"

DEFAULT_BUNDLES = [
    ROOT / "reports/park_geumja_patient_care_bundle_latest.json",
    ROOT / "reports/park_yeonwoo_patient_care_bundle_latest.json",
    ROOT / "reports/kim_haeun_patient_care_bundle_latest.json",
    ROOT / "reports/baeoksun_patient_care_bundle_latest.json",
    ROOT / "reports/soyoung_choi_patient_care_bundle_latest.json",
    ROOT / "reports/jiyoon_patient_care_bundle_latest.json",
]

_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]+")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _resolve_archived_41658() -> Path | None:
    candidates = sorted(
        PILOT.glob("master_codebook_lexicon_v1_41658_rows_archived_*_pre_hangul_curated.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _extract_bundle_text(doc: dict[str, Any]) -> str:
    parts: list[str] = []
    soap = doc.get("clinical_soap_v1") or {}
    for key in ("subjective", "objective", "assessment", "plan"):
        block = soap.get(key) or {}
        if isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
    for slot in doc.get("patient_slots") or []:
        if isinstance(slot, dict) and slot.get("body_markdown"):
            parts.append(str(slot["body_markdown"]))
    return "\n".join(parts)


def _snippet_stats(text: str, lex_path: Path) -> dict[str, Any]:
    hits, meta = lexicon_hits_for_text(text, lex_path, min_token_len=2)
    hangul_tokens = set(_HANGUL_RE.findall(text))
    hit_in_hangul = hits & hangul_tokens
    return {
        "lexicon_path": _rel(lex_path),
        "hit_count": len(hits),
        "hangul_token_count": len(hangul_tokens),
        "hits_intersect_hangul_tokens": len(hit_in_hangul),
        "hits_sample": sorted(hits)[:24],
        "meta_status": meta.get("status"),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--overlay-v2", type=Path, default=None, help="Optional v2 overlay lexicon.")
    args = ap.parse_args()

    p658 = _resolve_archived_41658()
    v2_sig = json.loads(V2_LEXICON_SIGNOFF.read_text(encoding="utf-8")) if V2_LEXICON_SIGNOFF.is_file() else {}
    prod_path = P41708 if v2_sig.get("approved") and P41708.is_file() else P41687
    prod_label = "production_41708" if prod_path == P41708 else "production_41687"
    if p658 is None or not prod_path.is_file():
        print("ABORT: lexicon paths missing", file=sys.stderr)
        return 1

    arms: list[tuple[str, Path]] = [
        ("archived_41658", p658),
        (prod_label, prod_path),
    ]
    if args.overlay_v2 and args.overlay_v2.is_file():
        arms.append(("overlay_v2_41658_plus_50", args.overlay_v2.resolve()))

    bundles_out: list[dict[str, Any]] = []
    for bpath in DEFAULT_BUNDLES:
        if not bpath.is_file():
            continue
        doc = json.loads(bpath.read_text(encoding="utf-8"))
        text = _extract_bundle_text(doc)
        row: dict[str, Any] = {
            "bundle_path": _rel(bpath),
            "encounter_ref": (doc.get("provenance") or {}).get("encounter_ref"),
            "text_chars": len(text),
            "arms": {label: _snippet_stats(text, path) for label, path in arms},
        }
        bundles_out.append(row)

    totals = {label: {"hit_count_sum": 0, "bundles": 0} for label, _ in arms}
    for b in bundles_out:
        for label, stats in b["arms"].items():
            totals[label]["hit_count_sum"] += int(stats.get("hit_count") or 0)
            totals[label]["bundles"] += 1

    doc = {
        "schema": "hangul_curated_clinical_snippet_lexicon_smoke_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "ms_paste_headline": "HOLD",
        "note": "Lookup-only smoke on patient_care_bundle text; not full evaluate_report compression.",
        "bundles": bundles_out,
        "aggregate": totals,
        "delta_production_minus_41658_hit_sum": (
            totals.get(prod_label, {}).get("hit_count_sum", 0)
            - totals.get("archived_41658", {}).get("hit_count_sum", 0)
        ),
        "production_lexicon_label": prod_label,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "bundles": len(bundles_out), "aggregate": totals}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
