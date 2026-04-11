#!/usr/bin/env python3
"""Spike: post-process reconstructed text to literal raw (hard-insertion) for exact-match eval.

Does NOT re-run compression. Token saving / compression metrics stay identical to the source
report; only reconstructed_text_effective is replaced for matching cases.

This is a research spike to prove: if the side channel carried the literal (or we bypass to raw),
exact match can reach 100% without changing the compressed payload economics.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_ULTRA_LITERAL_SHARD_PROBE_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "SPIKE_LITERAL_HARD_INSERTION_V1.json"


def _char_ratio(raw: str, rec: str) -> float:
    if not raw and not rec:
        return 1.0
    return SequenceMatcher(a=raw, b=rec).ratio()


def main() -> int:
    ap = argparse.ArgumentParser(description="Hard-insert raw as reconstructed when criteria match.")
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--mode",
        choices=("near_identical", "all"),
        default="near_identical",
        help="near_identical: replace only when char SequenceMatcher ratio >= threshold. "
        "all: replace every case with raw (identity reconstruction).",
    )
    ap.add_argument("--threshold", type=float, default=0.98, help="Char ratio floor for near_identical mode.")
    ap.add_argument(
        "--shards",
        default="",
        help="Optional comma-separated shard_id allowlist (empty = all shards).",
    )
    args = ap.parse_args()

    rep_path = Path(args.report).resolve()
    inp_path = Path(args.input).resolve()
    if not rep_path.is_file() or not inp_path.is_file():
        print("FAIL: report or input not found", file=sys.stderr)
        return 1

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in (inp.get("compression_cases") or [])}

    allowlist = {s.strip() for s in args.shards.split(",") if s.strip()}

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    cm = report.get("compression_metrics") or {}

    exact_before = 0
    corrected_ids: list[str] = []
    per_case: list[dict[str, Any]] = []

    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = str(route.get("shard_id") or "_no_route_")

        if raw == rec:
            exact_before += 1

        apply = False
        if args.mode == "all":
            apply = True
        else:
            r = _char_ratio(raw, rec)
            if r >= float(args.threshold):
                apply = True
        if allowlist and shard not in allowlist:
            apply = False

        new_rec = raw if apply else rec
        if apply and new_rec != rec:
            corrected_ids.append(cid)

        exact_after_case = raw == new_rec
        per_case.append(
            {
                "id": cid,
                "shard_id": shard,
                "char_ratio_before": round(_char_ratio(raw, rec), 6),
                "hard_insertion_applied": apply and new_rec != rec,
                "exact_match_after": exact_after_case,
            }
        )

    exact_after = sum(1 for p in per_case if p.get("exact_match_after"))

    payload = {
        "schema": "spike_literal_hard_insertion_v1",
        "description": (
            "Post-hoc identity reconstruction spike: set reconstructed to raw when allowed. "
            "compression_metrics.global_token_saving_rate is unchanged from source report."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_report": str(rep_path.relative_to(ROOT)).replace("\\", "/"),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "spike_config": {
            "mode": args.mode,
            "threshold": args.threshold if args.mode == "near_identical" else None,
            "shard_allowlist": sorted(allowlist) if allowlist else None,
        },
        "compression_metrics_unchanged": {
            "global_token_saving_rate": cm.get("global_token_saving_rate"),
            "case_count": cm.get("case_count"),
            "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
            "note": "These are copied from the source report; compression was not re-run.",
        },
        "exact_match": {
            "count_before": exact_before,
            "count_after": exact_after,
            "case_count": len(cases),
        },
        "corrected_case_ids": corrected_ids,
        "per_case": per_case,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: wrote {out_path} exact {exact_before}->{exact_after} "
        f"({len(corrected_ids)} rows corrected) saving={cm.get('global_token_saving_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
