#!/usr/bin/env python3
"""B-track: dissection of high-L2 jsonl vs pipeline4 4D mismatches (>= threshold)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
OUT = ROOT / "reports/logos_4d_high_l2_dissection_v1_latest.json"
OUT_MD = ROOT / "reports/logos_4d_high_l2_dissection_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _key(v: dict[str, float], places: int) -> tuple[float, ...]:
    return tuple(round(v[k], places) for k in ("S", "L", "K", "M"))


def _load_jsonl_rows(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid:
                out[vid] = row
    return out


def _pipe_vec(row: dict) -> dict[str, float] | None:
    p4 = row.get("pipeline4_unified_v2") or {}
    raw = p4.get("vector_4d") if isinstance(p4, dict) else None
    return coerce_4d(raw) if isinstance(raw, dict) else None


def dissection(*, jsonl: Path, full: Path, l2_min: float, places: int) -> dict:
    jrows = _load_jsonl_rows(jsonl)
    full_rows = json.loads(full.read_text(encoding="utf-8-sig"))
    high: list[dict] = []
    for row in full_rows:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "")
        if vid not in jrows:
            continue
        pv = _pipe_vec(row)
        if pv is None:
            continue
        jr = jrows[vid]
        jv = coerce_4d(jr.get("vector_4d") or jr.get("unified_4d_vector") or {})
        if _key(jv, places) == _key(pv, places):
            continue
        l2 = math.sqrt(sum((jv[k] - pv[k]) ** 2 for k in jv))
        if l2 < l2_min:
            continue
        text = str(jr.get("text") or "")[:120]
        high.append(
            {
                "verse_id": vid,
                "edition": jr.get("edition"),
                "decode_status": jr.get("decode_status"),
                "lexical_source": jr.get("lexical_source"),
                "hebrew_value": jr.get("hebrew_value"),
                "greek_value": jr.get("greek_value"),
                "total_value": jr.get("total_value"),
                "text_preview": text,
                "jsonl_4d": {k: round(jv[k], 6) for k in jv},
                "pipeline_4d": {k: round(pv[k], 6) for k in pv},
                "l2_delta": round(l2, 6),
                "hypothesis_class": (
                    "gematria_zero_jsonl"
                    if (jr.get("total_value") or 0) == 0
                    else "decode_path_divergence"
                ),
            }
        )
    high.sort(key=lambda x: x["l2_delta"], reverse=True)
    zero_gem = sum(1 for h in high if h["hypothesis_class"] == "gematria_zero_jsonl")
    return {
        "schema": "logos_4d_high_l2_dissection_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "l2_min": l2_min,
        "count": len(high),
        "gematria_zero_jsonl_count": zero_gem,
        "decode_path_divergence_count": len(high) - zero_gem,
        "verses": high,
        "operator_hint": (
            "High-L2 rows often share jsonl gematria=0 (morphhb WLC) while pipeline used MT decode path. "
            "Reconcile only with explicit human patch — not auto Track A."
        ),
    }


def _md(doc: dict) -> str:
    lines = [
        "# Logos 4D high-L2 dissection (B-track)",
        "",
        f"- count (L2>={doc['l2_min']}): **{doc['count']}**",
        f"- gematria_zero_jsonl: **{doc['gematria_zero_jsonl_count']}**",
        f"- decode_path_divergence: **{doc['decode_path_divergence_count']}**",
        "",
        "| verse_id | L2 | class | total_value |",
        "|----------|-----|-------|-------------|",
    ]
    for v in doc.get("verses") or []:
        lines.append(
            f"| `{v['verse_id']}` | {v['l2_delta']} | {v['hypothesis_class']} | {v.get('total_value')} |"
        )
    lines.extend(["", "[HYPO] · research_only", ""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--full", type=Path, default=FULL)
    ap.add_argument("--l2-min", type=float, default=0.2)
    ap.add_argument("--round-places", type=int, default=4)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()
    doc = dissection(jsonl=args.jsonl, full=args.full, l2_min=args.l2_min, places=max(1, args.round_places))
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "count": doc["count"], **{k: doc[k] for k in ("gematria_zero_jsonl_count", "decode_path_divergence_count")}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
