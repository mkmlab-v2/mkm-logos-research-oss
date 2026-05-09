#!/usr/bin/env python3
"""Aggregate token loss (raw vs reconstructed) on the general-rail eval input.

Profile defaults align with general-rail A/B treatment (sweep best_go: B/extreme/low caps).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report, _norm_words

DEFAULT_INPUT = ROOT / "docs/final/artifacts/general_compression_eval_input_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/general_compression_token_loss_aggregate_v1.json"

# Align with Run-GeneralCompressionChain treatment / sweep balanced best_go.
PROFILE = {
    "strategy": "B",
    "intensity": "extreme",
    "general_max_saving_rate": 0.2,
    "sensitive_max_saving_rate": 0.18,
    "hangul_max_saving_rate": 0.5,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="General-rail token loss aggregate (eval input cases).")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = json.loads(args.input.read_text(encoding="utf-8"))
    report = evaluate_report(
        doc,
        source_input=str(args.input),
        mode="experimental",
        strategy=PROFILE["strategy"],
        intensity=PROFILE["intensity"],
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        general_max_saving_rate=PROFILE["general_max_saving_rate"],
        sensitive_max_saving_rate=PROFILE["sensitive_max_saving_rate"],
        hangul_max_saving_rate=PROFILE["hangul_max_saving_rate"],
    )
    raw_by_id: dict[str, str] = {}
    for c in doc.get("compression_cases") or []:
        if isinstance(c, dict):
            raw_by_id[str(c.get("id", ""))] = str(c.get("raw_text", ""))

    global_lost = Counter()
    by_domain: dict[str, Counter] = {}
    case_rows: list[dict[str, Any]] = []

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        rw = _norm_words(raw)
        rr = _norm_words(rec)
        lost = rw - rr
        for t in lost:
            global_lost[t] += 1
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        dom = str(route.get("domain") or "unknown")
        if dom not in by_domain:
            by_domain[dom] = Counter()
        for t in lost:
            by_domain[dom][t] += 1
        case_rows.append(
            {
                "id": cid,
                "domain": dom,
                "shard_id": route.get("shard_id"),
                "lost_token_occurrences": len(lost),
                "lost_sorted_sample": sorted(lost)[:40],
            }
        )

    def top_n(ct: Counter, n: int) -> list[dict[str, Any]]:
        return [{"token": t, "count": c} for t, c in ct.most_common(n)]

    out = {
        "schema": "general_compression_token_loss_aggregate_v1",
        "source_input": str(args.input.resolve()),
        "profile": PROFILE,
        "compression_metrics_summary": {
            "global_token_saving_rate": (report.get("compression_metrics") or {}).get(
                "global_token_saving_rate"
            ),
            "avg_reconstruction_fidelity_jaccard": (report.get("compression_metrics") or {}).get(
                "avg_reconstruction_fidelity_jaccard"
            ),
        },
        "global_top_lost_tokens": top_n(global_lost, 50),
        "by_domain_top_lost_tokens": {d: top_n(ct, 25) for d, ct in sorted(by_domain.items())},
        "cases": case_rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve()), "unique_lost": len(global_lost)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
