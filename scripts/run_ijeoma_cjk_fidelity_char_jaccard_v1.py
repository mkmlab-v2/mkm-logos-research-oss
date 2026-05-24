#!/usr/bin/env python3
"""[HYPO] Char-level Jaccard for CJK substitution expand vs raw (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_hypo_v1.json"
HYPO_LEX = ROOT / "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_ijeoma_cjk_fidelity_char_jaccard_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def char_jaccard(a: str, b: str) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane-json", type=Path, default=LANE)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    lane_path = (ROOT / args.lane_json).resolve() if not args.lane_json.is_absolute() else args.lane_json
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    doc = json.loads(lane_path.read_text(encoding="utf-8"))
    scores: list[float] = []
    rows = []
    for case in doc.get("compression_cases") or []:
        raw = str(case.get("raw_text") or "")
        rec = str(case.get("reconstructed_text") or "")
        cj = round(char_jaccard(raw, rec), 4)
        scores.append(cj)
        rows.append({"case_id": case.get("id"), "char_jaccard": cj})

    mean_cj = sum(scores) / len(scores) if scores else 0.0
    out = {
        "schema": "comp_ijeoma_cjk_fidelity_char_jaccard_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "case_count": len(rows),
        "mean_char_jaccard": round(mean_cj, 4),
        "note": "Token Jaccard in evaluate_report stays high; char-level exposes substitution loss.",
        "rows": rows[:20],
        "rows_truncated": len(rows) > 20,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "mean_char_jaccard": mean_cj}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
