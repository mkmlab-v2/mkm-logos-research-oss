#!/usr/bin/env python3
"""Commander approval + MS-180d expansion + promotion parallel (wave 3)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/btrack_commander_approval_wave3_v1_latest.json"
WORK = ROOT / "reports/btrack_ms_180d_expansion_work"
SCORE_180 = WORK / "score_180d.json"
SIDECAR_180 = WORK / "sidecar_180d.json"
MS_180 = WORK / "ms_per_date_180d.json"
V1_PER_180 = WORK / "v1_per_date_180d.json"
V1_SCORE_180 = WORK / "v1_score_180d.json"
MATCHED_180 = ROOT / "reports/btrack_180d_active_day_matched_compare_v1_latest.json"
BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "").strip()[-500:],
    }


def _ms_180d_expansion(py: str, n_days: int = 180) -> dict[str, Any]:
    WORK.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    steps.append(
        _run(
            [
                py,
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--hypothesis-json",
                _rel(HYPO),
                "--btc-csv",
                _rel(BTC),
                "--kospi-csv",
                _rel(KOSPI),
                "--recent-trading-days",
                str(n_days),
                "--output",
                _rel(SCORE_180),
            ]
        )
    )
    if not steps[-1]["ok"]:
        return {"task_id": "ms_180d_expansion", "ok": False, "steps": steps}

    steps.append(
        _run(
            [
                py,
                "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py",
                "--score-json",
                _rel(SCORE_180),
                "--out",
                _rel(SIDECAR_180),
            ]
        )
    )
    if not steps[-1]["ok"]:
        return {"task_id": "ms_180d_expansion", "ok": False, "steps": steps}

    steps.append(
        _run(
            [
                py,
                "scripts/build_btrack_lens_combo_myeongni_sasang_per_date_v1.py",
                "--score-json",
                _rel(SCORE_180),
                "--sidecar-json",
                _rel(SIDECAR_180),
                "--output",
                _rel(MS_180),
            ]
        )
    )
    if not steps[-1]["ok"]:
        return {"task_id": "ms_180d_expansion", "ok": False, "steps": steps}

    ms_doc = json.loads(MS_180.read_text(encoding="utf-8"))
    n_rows = len(ms_doc.get("rows") or [])
    n_active = sum(
        1
        for r in ms_doc.get("rows") or []
        if isinstance(r, dict)
        and str(r.get("predicted_direction") or "") in ("bull", "bear")
    )

    steps.append(
        _run(
            [
                py,
                "scripts/build_btrack_ensemble_per_date_directions_v1.py",
                "--recent-trading-days",
                str(n_days),
                "--ensemble-mode",
                "v1",
                "--output",
                _rel(V1_PER_180),
            ]
        )
    )
    if not steps[-1]["ok"]:
        return {"task_id": "ms_180d_expansion", "ok": False, "steps": steps}

    steps.append(
        _run(
            [
                py,
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--hypothesis-json",
                _rel(HYPO),
                "--btc-csv",
                _rel(BTC),
                "--kospi-csv",
                _rel(KOSPI),
                "--recent-trading-days",
                str(n_days),
                "--per-date-direction-json",
                _rel(V1_PER_180),
                "--output",
                _rel(V1_SCORE_180),
            ]
        )
    )
    if not steps[-1]["ok"]:
        return {"task_id": "ms_180d_expansion", "ok": False, "steps": steps}

    steps.append(
        _run(
            [
                py,
                "scripts/run_btrack_active_day_matched_compare_v1.py",
                "--anchor-score",
                _rel(SCORE_180),
                "--v1-score",
                _rel(V1_SCORE_180),
                "--ms-per-date",
                _rel(MS_180),
                "--frozen-score",
                _rel(ROOT / "reports/btrack_prophecy_score_recommended_180d_v1.json"),
                "--output",
                _rel(MATCHED_180),
            ]
        )
    )
    matched = json.loads(MATCHED_180.read_text(encoding="utf-8")) if MATCHED_180.is_file() else {}
    return {
        "task_id": "ms_180d_expansion",
        "ok": steps[-1]["ok"],
        "steps": steps,
        "ms_per_date_rows": n_rows,
        "ms_directional_rows": n_active,
        "matched_panel": matched.get("panel"),
        "matched_lanes": {
            k: v.get("directional_hit_rate")
            for k, v in (matched.get("lanes") or {}).items()
            if isinstance(v, dict)
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--note",
        default="지휘관 승인(2026-05-19): 180d soft_band Track A candidate + MS-180d expansion. live/auto_bridge 별도.",
    )
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    py = sys.executable
    results: list[dict[str, Any]] = []

    fin = _run([py, "scripts/run_btrack_commander_approval_finalize_v1.py", "--reviewer", args.reviewer, "--note", args.note])
    results.append({"task_id": "commander_finalize", **fin})

    parallel_tasks: list[tuple[str, list[str]]] = [
        ("promotion_push", [py, "scripts/run_btrack_promotion_push_v1.py"]),
        ("hybrid_180d", [py, "scripts/run_btrack_hybrid_180d_promotion_parallel_v1.py", "--neutral-bps", "2.0"]),
        (
            "parallel_bundle",
            [
                py,
                "scripts/run_btrack_parallel_research_bundle_v1.py",
                "--skip-heavy",
                "--include-anchor-promotion",
            ],
        ),
    ]

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(_run, cmd): tid for tid, cmd in parallel_tasks}
        for fut in as_completed(futs):
            tid = futs[fut]
            r = fut.result()
            results.append({"task_id": tid, **r})

    ms_exp = _ms_180d_expansion(py)
    results.append(ms_exp)

    pack = {
        "schema": "btrack_commander_approval_wave3_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "reviewer": args.reviewer,
        "note": args.note,
        "tasks": results,
        "all_ok": all(r.get("ok") for r in results),
        "finalize_artifact": "reports/btrack_commander_approval_finalize_v1_latest.json",
        "live_trading_enabled": False,
    }
    args.output.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    lock = ROOT / "docs/final/artifacts/prophecy_manual_promotion_decision_lock_v1_latest.json"
    if lock.is_file():
        print(f"lock={json.loads(lock.read_text(encoding='utf-8')).get('final_decision')}")
    if ms_exp.get("matched_lanes"):
        print(f"180d matched lanes: {ms_exp.get('matched_lanes')}")
    return 0 if pack["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
