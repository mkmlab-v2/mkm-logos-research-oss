#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baseline SSOT manifest vs holdout-learned candidate — 30d/252d price ablation."""

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

from scripts.run_market_psych_v1_vs_v2_price_ablation_v1 import (  # noqa: E402
    BTC_CSV,
    PSYCH_V2,
    _eval_lane,
    _hit,
    _run,
)

DEFAULT_OUT = ROOT / "reports/market_psych_manifest_candidate_price_validation_v1_latest.json"
ARTIFACT_OUT = ROOT / "docs/final/artifacts/market_psych_manifest_candidate_price_validation_v1_latest.json"
SSOT_MANIFEST = ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"
CANDIDATE_MANIFEST = ROOT / "reports/market_psych_manifest_candidate_holdout_best_v1.json"
HOLDOUT_SWEEP = ROOT / "reports/market_psych_manifest_holdout_sweep_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_neutral_band(path: Path) -> float:
    doc = _load_json(path) or {}
    meta = doc.get("holdout_learning_v1") or {}
    try:
        return float(meta.get("neutral_band", 0.06))
    except (TypeError, ValueError):
        return 0.06


def _build_per_date(
    *,
    manifest: Path,
    neutral_band: float,
    out: Path,
    ensemble_mode: str,
) -> int:
    cmd = [
        sys.executable,
        "scripts/build_btrack_per_date_directions_market_psych_v2.py",
        "--market-psych-csv",
        str(PSYCH_V2),
        "--manifest-json",
        str(manifest),
        "--neutral-band",
        str(neutral_band),
        "--out",
        str(out),
    ]
    rc = _run(cmd)
    if rc == 0 and out.is_file():
        doc = _load_json(out) or {}
        doc["ensemble_mode"] = ensemble_mode
        doc["manifest_validation_lane"] = ensemble_mode
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-windows", type=int, nargs="+", default=[30, 252])
    ap.add_argument("--skip-yfinance", action="store_true", default=True)
    ap.add_argument("--candidate-manifest", type=Path, default=CANDIDATE_MANIFEST)
    ap.add_argument("--ssot-manifest", type=Path, default=SSOT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not PSYCH_V2.is_file():
        print(f"missing {PSYCH_V2}", file=sys.stderr)
        return 2
    if not args.ssot_manifest.is_file():
        print(f"missing {args.ssot_manifest}", file=sys.stderr)
        return 2
    if not args.candidate_manifest.is_file():
        print(f"missing {args.candidate_manifest}", file=sys.stderr)
        return 2

    if not args.skip_yfinance:
        if _run(
            [
                sys.executable,
                "scripts/build_market_psychology_kospi_from_yfinance_v2.py",
                "--days",
                "400",
            ]
        ):
            return 2

    nb_cand = _candidate_neutral_band(args.candidate_manifest)
    results: list[dict[str, Any]] = []

    for days in args.eval_windows:
        tag = f"{days}d"
        per_base = ROOT / f"reports/btrack_per_date_directions_manifest_ssot_{tag}.json"
        per_cand = ROOT / f"reports/btrack_per_date_directions_manifest_candidate_{tag}.json"
        if _build_per_date(
            manifest=args.ssot_manifest,
            neutral_band=0.06,
            out=per_base,
            ensemble_mode="market_psych_v2_ssot_manifest",
        ):
            return 2
        if _build_per_date(
            manifest=args.candidate_manifest,
            neutral_band=nb_cand,
            out=per_cand,
            ensemble_mode="market_psych_v2_candidate_manifest",
        ):
            return 2
        results.append(_eval_lane("manifest_ssot", per_base, days, tag))
        results.append(_eval_lane("manifest_candidate", per_cand, days, tag))

    def pick(lane: str, days: int) -> dict[str, Any] | None:
        for r in results:
            if r["lane_id"] == lane and r["eval_days"] == days:
                return r
        return None

    deltas: list[dict[str, Any]] = []
    for days in args.eval_windows:
        b = pick("manifest_ssot", days)
        c = pick("manifest_candidate", days)
        if not b or not c:
            continue
        k0 = (b.get("price_hit_rate") or {}).get("kospi")
        k1 = (c.get("price_hit_rate") or {}).get("kospi")
        deltas.append(
            {
                "eval_days": days,
                "kospi_ssot": k0,
                "kospi_candidate": k1,
                "kospi_candidate_minus_ssot_pp": round((float(k1) - float(k0)) * 100, 2)
                if k0 is not None and k1 is not None
                else None,
                "btc_ssot": (b.get("price_hit_rate") or {}).get("btc"),
                "btc_candidate": (c.get("price_hit_rate") or {}).get("btc"),
            }
        )

    sweep = _load_json(HOLDOUT_SWEEP)
    profile_id = (sweep or {}).get("best_on_train", {}).get("profile_id") or "unknown"

    doc = {
        "schema": "market_psych_manifest_candidate_price_validation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "not_promoted_track_a": True,
        "ssot_manifest_overwritten": False,
        "holdout_profile_id": profile_id,
        "candidate_neutral_band": nb_cand,
        "inputs": {
            "psych_v2_csv": str(PSYCH_V2.relative_to(ROOT)).replace("\\", "/"),
            "ssot_manifest": str(args.ssot_manifest.relative_to(ROOT)).replace("\\", "/"),
            "candidate_manifest": str(args.candidate_manifest.relative_to(ROOT)).replace("\\", "/"),
            "holdout_sweep": str(HOLDOUT_SWEEP.relative_to(ROOT)).replace("\\", "/"),
        },
        "lanes": results,
        "delta_candidate_minus_ssot": deltas,
        "verdict_ko": _verdict(deltas, profile_id),
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_OUT.write_text(text, encoding="utf-8")
    print(str(args.out.resolve()))
    return 0


def _verdict(deltas: list[dict[str, Any]], profile_id: str) -> str:
    parts = []
    for d in deltas:
        pp = d.get("kospi_candidate_minus_ssot_pp")
        if pp is None:
            continue
        parts.append(f"{d['eval_days']}d 코스피 candidate-ssot {pp:+.2f}pp")
    body = "; ".join(parts) if parts else "no delta"
    return (
        f"{body}. 후보={profile_id}(holdout train pick). "
        "SSOT manifest 미갱신 — 30d/252d 체인 재검증만. B-track, 승격·실매매 합선 금지."
    )


if __name__ == "__main__":
    raise SystemExit(main())
