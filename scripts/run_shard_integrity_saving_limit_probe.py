#!/usr/bin/env python3
"""Build a per-shard integrity vs saving observation map from a MULTILENS report.

This is a *probe* (single-run, fixed caps): it does not search for a Pareto frontier.
Use SHARD_INTEGRITY_SAVING_LIMIT_MAP_V1.json as Fact-Lock evidence of observed metrics
per DomainSpecificRouter shard_id for the given report + input.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_REPORT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_A_EXTREME_SOFT_TERMS_PLUS_QUALITY_V1.json"
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "SHARD_INTEGRITY_SAVING_LIMIT_MAP_V1.json"


def _rel_workspace(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _norm(s: str, nfc: bool) -> str:
    if nfc:
        return unicodedata.normalize("NFC", s)
    return s


def main() -> int:
    p = argparse.ArgumentParser(description="Shard integrity/saving probe from MULTILENS report JSON.")
    p.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="multilens_performance_eval_report_v1 JSON",
    )
    p.add_argument(
        "--input",
        type=Path,
        default=None,
        help="multilens_performance_eval_input_v1 JSON (defaults to report source_input)",
    )
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path")
    p.add_argument(
        "--nfc",
        action="store_true",
        help="Compare exact match after Unicode NFC normalization",
    )
    args = p.parse_args()

    rep_path = Path(args.report).resolve()
    if not rep_path.is_file():
        print(f"FAIL: report not found: {rep_path}", file=sys.stderr)
        return 1

    with rep_path.open(encoding="utf-8") as f:
        report: dict[str, Any] = json.load(f)

    inp_path = args.input
    if inp_path is None:
        src = report.get("source_input")
        if isinstance(src, str):
            inp_path = ROOT / src.replace("/", "\\") if sys.platform == "win32" else ROOT / src
        else:
            inp_path = DEFAULT_INPUT
    inp_path = Path(inp_path).resolve()
    if not inp_path.is_file():
        print(f"FAIL: input not found: {inp_path}", file=sys.stderr)
        return 1

    with inp_path.open(encoding="utf-8") as f:
        inp: dict[str, Any] = json.load(f)

    raw_by_id: dict[str, str] = {}
    for c in inp.get("compression_cases") or []:
        cid = str(c.get("id", ""))
        if cid:
            raw_by_id[cid] = str(c.get("raw_text", ""))

    cases = (report.get("compression_metrics") or {}).get("cases") or []
    if not cases:
        print("FAIL: no compression_metrics.cases in report", file=sys.stderr)
        return 1

    by_shard: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "case_count": 0,
            "exact_match_count": 0,
            "sum_token_saving_rate": 0.0,
            "sum_jaccard": 0.0,
            "sum_o200k_saving_rate": 0.0,
            "o200k_count": 0,
        }
    )

    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        nr = _norm(raw, args.nfc)
        nrec = _norm(rec, args.nfc)
        exact = nr == nrec

        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        shard = route.get("shard_id")
        sid = str(shard) if shard is not None else "_no_route_"

        agg = by_shard[sid]
        agg["case_count"] += 1
        if exact:
            agg["exact_match_count"] += 1
        agg["sum_token_saving_rate"] += float(row.get("token_saving_rate") or 0.0)
        agg["sum_jaccard"] += float(row.get("reconstruction_fidelity_jaccard") or 0.0)
        o2 = row.get("o200k_saving_rate")
        if o2 is not None:
            agg["sum_o200k_saving_rate"] += float(o2)
            agg["o200k_count"] += 1

    shards_out: list[dict[str, Any]] = []
    for sid in sorted(by_shard.keys()):
        agg = by_shard[sid]
        n = int(agg["case_count"])
        if n <= 0:
            continue
        o2c = int(agg["o200k_count"])
        shards_out.append(
            {
                "shard_id": sid,
                "case_count": n,
                "exact_match_count": int(agg["exact_match_count"]),
                "exact_match_rate": float(agg["exact_match_count"]) / float(n),
                "mean_token_saving_rate": float(agg["sum_token_saving_rate"]) / float(n),
                "mean_reconstruction_fidelity_jaccard": float(agg["sum_jaccard"]) / float(n),
                "mean_o200k_saving_rate": (
                    float(agg["sum_o200k_saving_rate"]) / float(o2c) if o2c else None
                ),
            }
        )

    payload = {
        "schema": "shard_integrity_saving_limit_map_v1",
        "description": (
            "Single-run observed metrics per router shard_id; not an optimized frontier. "
            "Regenerate after policy/cap changes or a new MULTILENS report."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "exact_match_definition": "unicode_nfc_equal" if args.nfc else "python_str_equal_raw_vs_reconstructed",
        "source_report": _rel_workspace(rep_path),
        "source_input": _rel_workspace(inp_path),
        "run_config_snapshot": report.get("run_config"),
        "shards": shards_out,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"OK: wrote {out_path} ({len(shards_out)} shards)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
