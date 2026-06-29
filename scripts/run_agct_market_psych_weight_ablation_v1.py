#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ablation: DNA-only vs market-psych-only vs 0.6/0.4 fusion — price hit-rate (B-track [HYPO])."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/agct_market_psych_weight_ablation_v1_latest.json"
ARTIFACT_OUT = ROOT / "docs/final/artifacts/agct_market_psych_weight_ablation_v1_latest.json"

PROFILES_ABLATION: tuple[tuple[str, float, float], ...] = (
    ("dna_only", 1.0, 0.0),
    ("market_psych_only", 0.0, 1.0),
    ("fusion_default", 0.6, 0.4),
)

# Market-rail sweep: dna_weight = 1 - market_weight (human DNA not mixed into index per-date).
MARKET_WEIGHT_GRID: tuple[float, ...] = (0.4, 0.6, 0.8, 1.0)


def _market_sweep_profiles() -> tuple[tuple[str, float, float], ...]:
    out: list[tuple[str, float, float]] = []
    for mw in MARKET_WEIGHT_GRID:
        pid = f"market_w{int(round(mw * 100)):02d}"
        out.append((pid, round(1.0 - mw, 2), mw))
    return tuple(out)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def _hit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"kospi": None, "btc": None, "n_evaluated": None, "status": "missing"}
    doc = json.loads(path.read_text(encoding="utf-8"))
    m = doc.get("metrics") or {}
    return {
        "kospi": m.get("price_directional_hit_rate"),
        "btc": m.get("price_directional_hit_rate"),
        "n_evaluated": m.get("n_evaluated"),
        "status": doc.get("status"),
    }


def _eval_profile(
    profile_id: str,
    dna_w: float,
    market_w: float,
    eval_days: int,
    psych_csv: Path,
    btc_csv: Path | None,
) -> dict[str, Any]:
    tag = f"ablation_{profile_id}_{eval_days}d"
    per_date = ROOT / f"reports/btrack_per_date_directions_{tag}.json"
    score_json = ROOT / f"reports/btrack_prophecy_score_{tag}.json"
    eval_kospi = ROOT / f"reports/prophecy_hit_rate_{tag}_kospi.json"
    eval_btc = ROOT / f"reports/prophecy_hit_rate_{tag}_btc.json"

    steps: list[dict[str, Any]] = []

    def step(name: str, cmd: list[str]) -> bool:
        rc = _run(cmd)
        steps.append({"step": name, "exit_code": rc})
        return rc == 0

    ok = step(
        "per_date",
        [
            sys.executable,
            "scripts/build_btrack_per_date_directions_agct_market_psych_v1.py",
            "--market-psych-csv",
            str(psych_csv),
            "--dna-weight",
            str(dna_w),
            "--market-weight",
            str(market_w),
            "--out",
            str(per_date),
        ],
    )
    if not ok:
        return {
            "profile_id": profile_id,
            "dna_weight": dna_w,
            "market_weight": market_w,
            "eval_days": eval_days,
            "ok": False,
            "steps": steps,
        }

    score_cmd = [
        sys.executable,
        "scripts/build_btrack_prophecy_score_from_ohlcv.py",
        "--per-date-direction-json",
        str(per_date),
        "--recent-trading-days",
        str(eval_days),
        "--output",
        str(score_json),
        "--force-dual-leg-panel",
    ]
    if btc_csv and btc_csv.is_file():
        score_cmd.extend(["--btc-csv", str(btc_csv)])
    if not step("prophecy_score", score_cmd):
        return {
            "profile_id": profile_id,
            "dna_weight": dna_w,
            "market_weight": market_w,
            "eval_days": eval_days,
            "ok": False,
            "steps": steps,
        }

    step(
        "eval_kospi",
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--headline-instrument",
            "kospi",
            "--output",
            str(eval_kospi),
        ],
    )
    step(
        "eval_btc",
        [
            sys.executable,
            "scripts/eval_prophecy_hit_rate_v1.py",
            "--run-mode",
            "price",
            "--score-json",
            str(score_json),
            "--headline-instrument",
            "btc",
            "--output",
            str(eval_btc),
        ],
    )

    # Unique predicted directions count (sanity: dna_only should be ~1)
    n_unique_dirs = None
    if per_date.is_file():
        rows = json.loads(per_date.read_text(encoding="utf-8")).get("rows") or []
        n_unique_dirs = len({r.get("predicted_direction") for r in rows})

    return {
        "profile_id": profile_id,
        "dna_weight": dna_w,
        "market_weight": market_w,
        "eval_days": eval_days,
        "ok": True,
        "n_unique_predicted_directions": n_unique_dirs,
        "price_hit_rate": {
            "kospi": _hit(eval_kospi)["kospi"],
            "btc": _hit(eval_btc)["btc"],
            "n_evaluated": _hit(eval_kospi)["n_evaluated"],
        },
        "artifacts": {
            "per_date_json": str(per_date.relative_to(ROOT)).replace("\\", "/"),
            "score_json": str(score_json.relative_to(ROOT)).replace("\\", "/"),
        },
        "steps": steps,
    }


def _best_kospi_by_window(results: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    best: dict[str, dict[str, Any] | None] = {"30": None, "252": None}
    for days in (30, 252):
        candidates = [
            r
            for r in results
            if r.get("ok") and int(r.get("eval_days") or 0) == days
        ]
        if not candidates:
            continue
        best[str(days)] = max(
            candidates,
            key=lambda r: float((r.get("price_hit_rate") or {}).get("kospi") or -1.0),
        )
    return best


def _verdict_ko(results: list[dict[str, Any]], *, profile_set: str) -> str:
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for r in results:
        if not r.get("ok"):
            continue
        by_key[(str(r["profile_id"]), int(r["eval_days"]))] = r

    def kospi(pid: str, days: int) -> float | None:
        row = by_key.get((pid, days))
        if not row:
            return None
        return (row.get("price_hit_rate") or {}).get("kospi")

    lines: list[str] = []
    for days in (30, 252):
        d = kospi("dna_only", days)
        m = kospi("market_psych_only", days)
        f = kospi("fusion_default", days)
        if d is None or m is None or f is None:
            continue
        best = max(
            [("dna_only", d), ("market_psych_only", m), ("fusion_default", f)],
            key=lambda x: x[1],
        )
        lines.append(
            f"{days}d 코스피: DNA고정 {d*100:.1f}% · 심리만 {m*100:.1f}% · 융합0.6/0.4 {f*100:.1f}% "
            f"(최고={best[0]})."
        )
    if profile_set == "market_sweep":
        b = _best_kospi_by_window(
            [r for r in results if str(r.get("profile_id", "")).startswith("market_w")]
        )
        parts: list[str] = []
        for days, row in b.items():
            if not row:
                continue
            hr = (row.get("price_hit_rate") or {}).get("kospi")
            parts.append(
                f"{days}d 코스피 최고= {row.get('profile_id')} "
                f"(dna={row.get('dna_weight')}, market={row.get('market_weight')}) "
                f"{float(hr)*100:.1f}%"
                if hr is not None
                else f"{days}d 실패"
            )
        if parts:
            return (
                " ".join(parts)
                + " 시장 per-date 레일 권장: market_weight≥0.8 또는 1.0(DNA prior 제외). "
                "인간/코호트 AGCT는 별 체인. research_only, 승격 없음."
            )
        return "market_weight sweep 일부 실패."

    if not lines:
        return "ablation 일부 실패 — steps 확인."
    return (
        " ".join(lines)
        + " DNA-only는 일별 방향이 거의 고정(코호트 prior). "
        "융합이 항상 최고는 아님 — research_only, 승격 없음."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--profile-set",
        choices=("ablation", "market_sweep"),
        default="ablation",
        help="ablation=DNA/market/fusion; market_sweep=market_weight grid for index rail.",
    )
    ap.add_argument("--eval-windows", type=int, nargs="+", default=[30, 252])
    ap.add_argument("--psych-days", type=int, default=400)
    ap.add_argument("--skip-yfinance", action="store_true", default=True)
    ap.add_argument("--refresh-yfinance", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    if args.out is None:
        args.out = (
            ROOT / "reports/agct_market_psych_market_weight_sweep_v1_latest.json"
            if args.profile_set == "market_sweep"
            else DEFAULT_OUT
        )
    profiles = (
        _market_sweep_profiles()
        if args.profile_set == "market_sweep"
        else PROFILES_ABLATION
    )

    psych_csv = ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_latest.csv"
    btc_csv = ROOT / "research/market_data/btc_daily_external_yf.csv"

    if args.refresh_yfinance or not psych_csv.is_file():
        rc = _run(
            [
                sys.executable,
                "scripts/build_market_psychology_kospi_from_yfinance_v1.py",
                "--days",
                str(args.psych_days),
            ]
        )
        if rc != 0:
            return rc

    if not psych_csv.is_file():
        print(f"missing {psych_csv}", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for profile_id, dna_w, market_w in profiles:
        for eval_days in args.eval_windows:
            print(f"=== {profile_id} dna={dna_w} market={market_w} eval_days={eval_days} ===")
            results.append(
                _eval_profile(profile_id, dna_w, market_w, eval_days, psych_csv, btc_csv)
            )

    hybrid = None
    hp = ROOT / "reports/session_myeongni_hybrid_holdout_252d_v1.json"
    h30 = ROOT / "reports/session_myeongni_ab_hybrid_30d_v1.json"
    if hp.is_file():
        hybrid = {"252d": json.loads(hp.read_text(encoding="utf-8"))}
    if h30.is_file():
        hybrid = hybrid or {}
        hybrid["30d"] = json.loads(h30.read_text(encoding="utf-8"))

    artifact_out = (
        ROOT / "docs/final/artifacts/agct_market_psych_market_weight_sweep_v1_latest.json"
        if args.profile_set == "market_sweep"
        else ARTIFACT_OUT
    )

    operating_principle = {
        "human_rail": "AGCT/DNA·출생 명리·환자 번들 — 가격 per-date에 자동 합선 금지",
        "market_rail": "일별 시장심리(yfinance→4축 휴리스틱)·OHLC·1차 regime_map",
        "price_per_date_default_research": {"dna_weight": 0.0, "market_weight": 1.0},
        "b_track_cohort_fusion_legacy": {"dna_weight": 0.6, "market_weight": 0.4},
    }

    doc = {
        "schema": (
            "agct_market_psych_market_weight_sweep_v1"
            if args.profile_set == "market_sweep"
            else "agct_market_psych_weight_ablation_v1"
        ),
        "profile_set": args.profile_set,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "not_promoted_track_a": True,
        "operating_principle_v1": operating_principle,
        "profiles": [{"id": p, "dna_weight": d, "market_weight": m} for p, d, m in profiles],
        "eval_windows": list(args.eval_windows),
        "note_ko": (
            "dna_only: 코호트 AGCT 축 고정 → 날짜별 방향 거의 동일. "
            "market_psych_only: yfinance 심리→4축만 일별 변동. "
            "fusion_default: B-track 코호트 융합 0.6/0.4(가격 레일 기본값 아님)."
            if args.profile_set == "ablation"
            else "시장 예측 per-date: market_weight 그리드. DNA prior는 1-market_weight만."
        ),
        "best_kospi_by_window": {
            str(k): (
                {
                    "profile_id": v.get("profile_id"),
                    "dna_weight": v.get("dna_weight"),
                    "market_weight": v.get("market_weight"),
                    "kospi_hit_rate": (v.get("price_hit_rate") or {}).get("kospi"),
                }
                if v
                else None
            )
            for k, v in _best_kospi_by_window(results).items()
        },
        "runs": results,
        "reference_session_hybrid_kospi": {
            "30d": (hybrid or {})
            .get("30d", {})
            .get("comparison_eval_prophecy_hit_rate", {})
            .get("hybrid_session_kospi_btc_bear", {})
            .get("kospi")
            if hybrid
            else None,
            "252d": (hybrid or {})
            .get("252d", {})
            .get("eval_prophecy_hit_rate", {})
            .get("hybrid", {})
            .get("kospi")
            if hybrid
            else None,
        },
        "verdict_ko": _verdict_ko(results, profile_set=args.profile_set),
    }

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    artifact_out.parent.mkdir(parents=True, exist_ok=True)
    artifact_out.write_text(text, encoding="utf-8")
    print(str(args.out.resolve()))
    failed = sum(1 for r in results if not r.get("ok"))
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
