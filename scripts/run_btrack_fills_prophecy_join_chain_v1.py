#!/usr/bin/env python3
"""[HYPO] One-shot: fills execution-eval lane → fills×prophecy shadow join (research_only)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts" / "run_btrack_fills_execution_eval_lane_v1.py"
JOIN = ROOT / "scripts" / "join_btrack_fills_prophecy_panel_v1.py"
CORR = ROOT / "scripts" / "correlate_btrack_joined_wide_csv_v1.py"
DIR_HIT = ROOT / "scripts" / "build_btrack_fills_prophecy_direction_hit_v1.py"
BAND = ROOT / "scripts" / "build_btrack_fills_execution_band_report_v1.py"
DEFAULT_OVERLAP_CSV = ROOT / "reports/btrack_fills_prophecy_join_overlap_v1_latest.csv"
DEFAULT_CORR_JSON = ROOT / "reports/btrack_fills_prophecy_join_correlation_v1_latest.json"
DEFAULT_DIR_HIT_JSON = ROOT / "reports/btrack_fills_prophecy_direction_hit_v1_latest.json"
DEFAULT_SUMMARY = ROOT / "reports/btrack_fills_prophecy_join_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _top_correlations(doc: dict[str, object], *, limit: int = 5) -> list[dict[str, object]]:
    rows = doc.get("correlations")
    if not isinstance(rows, list):
        return []
    computed = [r for r in rows if isinstance(r, dict) and r.get("status") == "computed"]
    computed.sort(
        key=lambda r: abs(float(r.get("pearson_r") or 0.0)),
        reverse=True,
    )
    out: list[dict[str, object]] = []
    for r in computed[:limit]:
        out.append(
            {
                "x_col": r.get("x_col"),
                "y_col": r.get("y_col"),
                "n_pairs": r.get("n_pairs"),
                "pearson_r": r.get("pearson_r"),
                "spearman_r": r.get("spearman_r"),
            }
        )
    return out


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}", file=sys.stderr)
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-eval-lane", action="store_true")
    ap.add_argument("--skip-correlate", action="store_true")
    ap.add_argument("--skip-direction-hit", action="store_true")
    ap.add_argument("--skip-fills-band-report", action="store_true")
    ap.add_argument("--spine", choices=("union", "fills", "prophecy"), default="union")
    ap.add_argument("--per-date-json", type=Path, default=None)
    ap.add_argument("--overlap-csv", type=Path, default=DEFAULT_OVERLAP_CSV)
    ap.add_argument("--corr-out-json", type=Path, default=DEFAULT_CORR_JSON)
    ap.add_argument("--corr-y-col", type=str, default="fill_realized_pnl_sum")
    ap.add_argument("--corr-min-pairs", type=int, default=3)
    ap.add_argument("--direction-hit-out-json", type=Path, default=DEFAULT_DIR_HIT_JSON)
    ap.add_argument("--out-summary-json", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    steps: list[dict[str, object]] = []
    if not args.skip_eval_lane:
        rc = _run([sys.executable, str(EVAL)])
        steps.append({"step": "run_btrack_fills_execution_eval_lane_v1", "exit_code": rc})
        if rc != 0:
            return rc

    join_cmd = [sys.executable, str(JOIN), "--spine", args.spine]
    if args.per_date_json is not None:
        join_cmd.extend(["--per-date-json", str(args.per_date_json)])
    rc = _run(join_cmd)
    steps.append({"step": "join_btrack_fills_prophecy_panel_v1", "exit_code": rc})
    if rc != 0:
        return rc

    corr_doc: dict[str, object] | None = None
    if not args.skip_correlate:
        if not args.overlap_csv.is_file():
            print(f"missing overlap csv: {args.overlap_csv}", file=sys.stderr)
            return 1
        corr_cmd = [
            sys.executable,
            str(CORR),
            "--input-csv",
            str(args.overlap_csv),
            "--y-col",
            args.corr_y_col,
            "--x-auto-prefixes",
            "prp_,fill_",
            "--min-pairs",
            str(max(2, int(args.corr_min_pairs))),
            "--out-json",
            str(args.corr_out_json),
        ]
        rc = _run(corr_cmd)
        steps.append({"step": "correlate_btrack_joined_wide_csv_v1", "exit_code": rc})
        if rc != 0:
            return rc
        if args.corr_out_json.is_file():
            corr_doc = json.loads(args.corr_out_json.read_text(encoding="utf-8-sig"))

    dir_hit_doc: dict[str, object] | None = None
    if not args.skip_direction_hit:
        if not args.overlap_csv.is_file():
            print(f"missing overlap csv: {args.overlap_csv}", file=sys.stderr)
            return 1
        hit_cmd = [
            sys.executable,
            str(DIR_HIT),
            "--overlap-csv",
            str(args.overlap_csv),
            "--out-json",
            str(args.direction_hit_out_json),
        ]
        rc = _run(hit_cmd)
        steps.append({"step": "build_btrack_fills_prophecy_direction_hit_v1", "exit_code": rc})
        if rc != 0:
            return rc
        if args.direction_hit_out_json.is_file():
            dir_hit_doc = json.loads(args.direction_hit_out_json.read_text(encoding="utf-8-sig"))

    if not args.skip_fills_band_report:
        rc = _run([sys.executable, str(BAND)])
        steps.append({"step": "build_btrack_fills_execution_band_report_v1", "exit_code": rc})
        if rc != 0:
            return rc

    summary = {
        "schema": "btrack_fills_prophecy_join_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "steps": steps,
        "outputs": {
            "overlap_csv": str(args.overlap_csv),
            "correlation_json": str(args.corr_out_json) if not args.skip_correlate else None,
            "direction_hit_json": str(args.direction_hit_out_json) if not args.skip_direction_hit else None,
        },
        "correlation_top_computed": _top_correlations(corr_doc) if corr_doc else [],
        "direction_hit_summary": (
            {
                "ohlcv_hit_rate": (dir_hit_doc.get("ohlcv_leg") or {}).get("directional_hit_rate")
                if isinstance(dir_hit_doc.get("ohlcv_leg"), dict)
                else None,
                "pnl_hit_rate": (dir_hit_doc.get("pnl_leg") or {}).get("directional_hit_rate")
                if isinstance(dir_hit_doc.get("pnl_leg"), dict)
                else None,
                "n_rows_scored": dir_hit_doc.get("overlap_counts", {}).get("n_rows_scored")
                if isinstance(dir_hit_doc.get("overlap_counts"), dict)
                else None,
            }
            if dir_hit_doc
            else None
        ),
        "chain_ok": True,
    }
    args.out_summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": True, "summary": str(args.out_summary_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
