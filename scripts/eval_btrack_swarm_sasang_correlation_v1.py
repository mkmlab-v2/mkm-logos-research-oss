#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate Swarm×Sasang vs OHLCV correlations with pre-registered gates ([HYPO]).

Runs ``correlate_btrack_joined_wide_csv_v1.py`` then applies Benjamini-Hochberg FDR and
hypothesis register success criteria. Writes ``reports/btrack_swarm_sasang_correlation_v1_latest.json``.

Null result is a valid Stage-0 outcome (fusion code still forbidden).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTER = ROOT / "docs" / "final" / "artifacts" / "btrack_swarm_sasang_hypothesis_register_v1.json"
DEFAULT_OUT = ROOT / "reports" / "btrack_swarm_sasang_correlation_v1_latest.json"
CORR_SCRIPT = ROOT / "scripts" / "correlate_btrack_joined_wide_csv_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bh_adjust(p_values: list[float | None]) -> list[float | None]:
    indexed = [(i, p) for i, p in enumerate(p_values) if p is not None]
    if not indexed:
        return [None] * len(p_values)
    m = len(indexed)
    order = sorted(indexed, key=lambda x: x[1])
    adjusted_map: dict[int, float] = {}
    prev = 1.0
    for rank in range(m, 0, -1):
        i, p = order[rank - 1]
        q = min(prev, p * m / rank)
        prev = q
        adjusted_map[i] = q
    out: list[float | None] = []
    for i, p in enumerate(p_values):
        out.append(adjusted_map.get(i))
    return out


def _load_register(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-csv", type=Path, required=True, help="Wide CSV after join + sasang enrich")
    ap.add_argument("--y-col", type=str, default=None)
    ap.add_argument(
        "--x-auto-prefixes",
        type=str,
        default="swarm_,sasang_",
    )
    ap.add_argument("--min-pairs", type=int, default=None)
    ap.add_argument("--register-json", type=Path, default=DEFAULT_REGISTER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--corr-json-tmp", type=Path, default=None)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    if not args.input_csv.is_file():
        print(f"missing input csv: {args.input_csv}", file=sys.stderr)
        return 2
    if not CORR_SCRIPT.is_file():
        print(f"missing correlate script: {CORR_SCRIPT}", file=sys.stderr)
        return 2

    reg = _load_register(args.register_json)
    success = reg.get("success_criteria") if isinstance(reg.get("success_criteria"), dict) else {}
    y_col = args.y_col or str(reg.get("default_y_col") or "ohlcv_close")
    min_pairs = args.min_pairs if args.min_pairs is not None else int(success.get("min_pairs") or 3)
    min_r = float(success.get("min_pearson_r_abs") or 0.3)
    max_p_fdr = float(success.get("max_p_value_fdr_bh") or 0.05)

    tmp_corr = args.corr_json_tmp or args.out_json.with_suffix(".corr_tmp.json")
    cmd = [
        sys.executable,
        str(CORR_SCRIPT),
        "--input-csv",
        str(args.input_csv),
        "--y-col",
        y_col,
        "--x-auto-prefixes",
        args.x_auto_prefixes,
        "--min-pairs",
        str(min_pairs),
        "--out-json",
        str(tmp_corr),
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        return rc
    corr_doc = json.loads(tmp_corr.read_text(encoding="utf-8"))
    correlations_in = corr_doc.get("correlations") if isinstance(corr_doc.get("correlations"), list) else []

    p_raw: list[float | None] = []
    for c in correlations_in:
        p_raw.append(c.get("p_value_pearson") if isinstance(c, dict) else None)
    p_fdr = _bh_adjust(p_raw)

    evaluated: list[dict[str, Any]] = []
    n_pass = 0
    for idx, c in enumerate(correlations_in):
        if not isinstance(c, dict):
            continue
        pr = c.get("pearson_r")
        n_pairs = int(c.get("n_pairs") or 0)
        pf = p_fdr[idx]
        abs_r = abs(float(pr)) if pr is not None else None
        sig = (
            c.get("status") == "computed"
            and pf is not None
            and pf <= max_p_fdr
            and abs_r is not None
            and abs_r >= min_r
            and n_pairs >= min_pairs
        )
        if sig:
            n_pass += 1
        evaluated.append(
            {
                **c,
                "p_value_pearson_fdr_bh": pf,
                "significance_pass_preregistered": sig,
            }
        )

    stage = 0
    stage_label = "null_or_insufficient"
    if n_pass > 0:
        stage = 0
        stage_label = "exploratory_pair_pass_still_research_only"
    elif any(c.get("status") == "computed" for c in evaluated):
        stage = 0
        stage_label = "null_under_preregistered_gates"

    track_wall = reg.get("track_wall") if isinstance(reg.get("track_wall"), dict) else {}
    payload = {
        "schema": "btrack_swarm_sasang_correlation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "hypothesis_register": str(args.register_json.resolve()).replace("\\", "/"),
        "h0": reg.get("h0"),
        "inputs": {
            "wide_csv": str(args.input_csv.resolve()),
            "correlation_intermediate": str(tmp_corr.resolve()),
        },
        "params": {
            "y_col": y_col,
            "x_auto_prefixes": args.x_auto_prefixes,
            "min_pairs": min_pairs,
            "min_pearson_r_abs": min_r,
            "max_p_value_fdr_bh": max_p_fdr,
        },
        "correlations": evaluated,
        "verdict": {
            "n_pairs_tested": len(evaluated),
            "n_significance_pass_preregistered": n_pass,
            "any_significance_pass": n_pass > 0,
            "stage": stage,
            "stage_label": stage_label,
            "fusion_pipeline_merge_allowed": False,
            "track_a_promotion": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
        "track_wall": track_wall,
        "note_ko": (
            "Stage 0 B-track 샌드박스. 유의성 통과여도 Track A·live·PersonaDiary 본선 합선 금지. "
            "null이면 weather×명리 로드맵과 동일하게 fusion 코드 추가 금지."
        ),
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        sys.stdout.write(text)
        return 0
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(str(args.out_json.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
