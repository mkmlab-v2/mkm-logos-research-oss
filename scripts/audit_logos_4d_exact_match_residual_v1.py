#!/usr/bin/env python3
"""B-track: sample and categorize jsonl vs pipeline4 4D mismatches after promotion."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
OUT = ROOT / "reports/logos_4d_exact_match_residual_v1_latest.json"
OUT_MD = ROOT / "reports/logos_4d_exact_match_residual_v1_latest.md"
FALLBACK = (0.25, 0.25, 0.25, 0.25)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _key(v: dict[str, float], places: int) -> tuple[float, ...]:
    return tuple(round(v[k], places) for k in ("S", "L", "K", "M"))


def _load_jsonl(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid:
                out[vid] = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
    return out


def _pipe_vec(row: dict) -> dict[str, float] | None:
    p4 = row.get("pipeline4_unified_v2") or {}
    raw = p4.get("vector_4d") if isinstance(p4, dict) else None
    return coerce_4d(raw) if isinstance(raw, dict) else None


def analyze(*, jsonl: Path, full: Path, places: int, sample: int) -> dict:
    jidx = _load_jsonl(jsonl)
    rows = json.loads(full.read_text(encoding="utf-8-sig"))
    compared = exact = 0
    mismatches: list[dict] = []
    l2_buckets = Counter()
    j_fb = p_fb = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "")
        if vid not in jidx:
            continue
        pv = _pipe_vec(row)
        if pv is None:
            continue
        jv = jidx[vid]
        compared += 1
        jk, pk = _key(jv, places), _key(pv, places)
        if jk == FALLBACK:
            j_fb += 1
        if pk == FALLBACK:
            p_fb += 1
        if jk == pk:
            exact += 1
            continue
        l2 = math.sqrt(sum((jv[k] - pv[k]) ** 2 for k in jv))
        if l2 < 0.01:
            bucket = "l2_lt_0.01"
        elif l2 < 0.05:
            bucket = "l2_0.01_0.05"
        elif l2 < 0.2:
            bucket = "l2_0.05_0.2"
        else:
            bucket = "l2_ge_0.2"
        l2_buckets[bucket] += 1
        mismatches.append(
            {
                "verse_id": vid,
                "jsonl_4d": {k: round(jv[k], 6) for k in jv},
                "pipeline_4d": {k: round(pv[k], 6) for k in pv},
                "l2_delta": round(l2, 6),
                "bucket": bucket,
            }
        )
    mismatches.sort(key=lambda x: x["l2_delta"], reverse=True)
    mismatch_n = compared - exact
    return {
        "schema": "logos_4d_exact_match_residual_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "inputs": {"jsonl": _rel(jsonl), "full_pipeline_json": _rel(full), "round_places": places},
        "summary": {
            "compared": compared,
            "exact_match": exact,
            "exact_match_rate": round(exact / compared, 6) if compared else 0.0,
            "mismatch_count": mismatch_n,
            "mismatch_rate": round(mismatch_n / compared, 6) if compared else 0.0,
            "jsonl_fallback_at_places": j_fb,
            "pipeline_fallback_at_places": p_fb,
            "l2_buckets": dict(l2_buckets),
        },
        "top_mismatch_samples": mismatches[:sample],
        "operator_hint": (
            "Residuals are decode-path / rounding / source-text differences between jsonl (BHS+SBLGNT) "
            "and 4pipeline (MT canon). Not prophecy calibration. Reconcile only with explicit B-track patch."
        ),
        "track_wall": {"a_track_auto_promotion": False, "live_trading": False},
    }


def _md(doc: dict) -> str:
    s = doc["summary"]
    lines = [
        "# Logos 4D exact-match residual (B-track)",
        "",
        f"- generated: {doc['generated_at_utc']}",
        f"- compared: **{s['compared']}**",
        f"- exact: **{s['exact_match']}** ({s['exact_match_rate']:.2%})",
        f"- mismatch: **{s['mismatch_count']}** ({s['mismatch_rate']:.2%})",
        f"- jsonl fallback @4dp: **{s['jsonl_fallback_at_places']}** · pipeline: **{s['pipeline_fallback_at_places']}**",
        "",
        "## L2 buckets",
        "",
    ]
    for k, v in sorted(s["l2_buckets"].items()):
        lines.append(f"- `{k}`: {v}")
    lines.extend(["", "## Top samples (by L2)", ""])
    for row in doc.get("top_mismatch_samples") or []:
        lines.append(f"- `{row['verse_id']}` L2={row['l2_delta']} · {row['bucket']}")
    lines.extend(["", "[HYPO] · research_only · `[NON_GATING]`", ""])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--full", type=Path, default=FULL)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--round-places", type=int, default=4)
    ap.add_argument("--sample", type=int, default=40)
    args = ap.parse_args()
    if not args.jsonl.is_file() or not args.full.is_file():
        print(json.dumps({"ok": False, "error": "missing inputs"}))
        return 2
    doc = analyze(jsonl=args.jsonl, full=args.full, places=max(1, args.round_places), sample=max(1, args.sample))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
