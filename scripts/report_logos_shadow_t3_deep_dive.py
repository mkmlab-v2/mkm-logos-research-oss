#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T3 window (2023-2024) focused debug: full warnings dump + aggregate diagnostics (OBSERVATION_ONLY)."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_lib_path = Path(__file__).resolve().parent / "logos_shadow_eval_lib.py"
_spec = importlib.util.spec_from_file_location("logos_shadow_eval_lib", _lib_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load {_lib_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
DEFAULT_SHADOW_EXTRA = _mod.DEFAULT_SHADOW_EXTRA_ARGS
load_kospi_yf_rows = _mod.load_kospi_yf_rows

DEFAULT_DATA = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
OUT_DIR = ROOT / "reports" / "research" / "logos_shadow_v1"
DEFAULT_OUT = OUT_DIR / "logos_kospi_shadow_t3_deep_dive_latest.json"

T3 = ("t3_2023_2024_recent", "2023-01-01", "2024-12-31")


def _histogram_evidence(warnings: list[dict[str, Any]]) -> dict[str, int]:
    c = Counter()
    for w in warnings:
        c[str(int(w.get("evidence_count", 0)))] += 1
    return dict(sorted(c.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0))


def _channel_freq(warnings: list[dict[str, Any]]) -> dict[str, int]:
    c = Counter()
    for w in warnings:
        for ch in w.get("evidence_channels") or []:
            c[str(ch)] += 1
    return dict(c.most_common())


def main() -> int:
    ap = argparse.ArgumentParser(description="T3 deep-dive: detail JSON + diagnostics.")
    ap.add_argument("--data-csv", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--bare", action="store_true", help="Pass no DEFAULT_SHADOW_EXTRA (legacy raw).")
    args, extra = ap.parse_known_args()

    extra_list = list(extra)
    if not extra_list and not args.bare:
        extra_list = list(DEFAULT_SHADOW_EXTRA)

    wname, s, e = T3
    rows = [r for r in load_kospi_yf_rows(args.data_csv) if s <= r["date"] <= e]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    p_in = args.out_dir / f"{wname}_deep_dive_input.json"
    p_in.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    p_detail = args.out_dir / f"{wname}_detail_full.json"

    cmd = [
        sys.executable,
        str(args.script),
        "--input-json",
        str(p_in),
        "--out-dir",
        str(args.out_dir),
        "--detail-json",
        str(p_detail),
    ] + extra_list
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr or cp.stdout or "")
        return 1

    detail = json.loads(p_detail.read_text(encoding="utf-8"))
    warnings = detail.get("warnings") or []
    per_s = detail.get("per_warning_summary") or []
    crash_indices = detail.get("crash_indices") or []

    in_pz = sum(1 for x in per_s if x.get("in_precrash_zone"))
    m_back = 20
    recalled = 0
    for ci in crash_indices:
        left = max(0, ci - m_back)
        has_w = any(left <= int(w["index"]) < ci for w in warnings)
        if has_w:
            recalled += 1
    recall_diag = {
        "crash_event_count": len(crash_indices),
        "recalled_by_warning_in_precrash_window": recalled,
        "recall_fraction": (recalled / len(crash_indices)) if crash_indices else None,
        "note": "Matches run_logos_kospi_shadow_test crash_warning_recall definition (warning in [ci-20, ci)).",
    }

    payload: dict[str, Any] = {
        "schema": "logos_kospi_shadow_t3_deep_dive_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"id": wname, "period": [s, e], "rows": len(rows)},
        "extra_args": extra_list,
        "detail_json_path": str(p_detail.resolve()),
        "evidence_count_histogram": _histogram_evidence(warnings),
        "evidence_channel_totals": _channel_freq(warnings),
        "warnings_in_precrash_zone": in_pz,
        "warnings_not_in_precrash_zone": len(warnings) - in_pz,
        "recall_diagnosis": recall_diag,
        "hypothesis_hooks": [
            "If recall_diagnosis.recall_fraction is 0 but crash_event_count > 0, warnings are not landing in [ci-20,ci) for labeled crashes (threshold/sparsification/precision layer).",
            "Compare evidence_count_histogram to recent_precision_min_evidence filter (default 3 in DEFAULT_SHADOW_EXTRA).",
        ],
        "observation_only": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "detail": str(p_detail.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
