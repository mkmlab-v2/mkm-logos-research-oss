#!/usr/bin/env python3
"""Score prior-day commander hypothesis branches vs KOSPI close [B-track][HYPO].

P31d input — does not mutate Track A or live trading.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
LOG_DIR = ROOT / "reports" / "hypothesis_log"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "commander_hypothesis_branch_scores_latest.json"

SCORE_LABELS = ("aligned", "partial", "neutral", "not_scored", "insufficient_data")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _kospi_return_for_date(csv_path: Path, date_kst: str) -> Tuple[Optional[float], str]:
    try:
        from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: WPS433
    except ImportError:
        return None, "logos_shadow_eval_lib_missing"

    rows = load_kospi_yf_rows(csv_path)
    if not rows:
        return None, "no_rows"
    by_date = {str(r.get("date") or "")[:10]: r for r in rows if r.get("date")}
    if date_kst not in by_date:
        return None, "date_missing"
    target = by_date[date_kst]
    close = float(target.get("close") or 0)
    dates_sorted = sorted(by_date.keys())
    idx = dates_sorted.index(date_kst)
    if idx < 1:
        return None, "no_prior_close"
    prev = by_date[dates_sorted[idx - 1]]
    prev_close = float(prev.get("close") or 0)
    if prev_close <= 0:
        return None, "bad_prior"
    ret = (close - prev_close) / prev_close
    direction = "up" if ret > 0.001 else ("down" if ret < -0.001 else "flat")
    return ret, direction


def _score_branch(
    branch: Dict[str, Any],
    *,
    market_direction: str,
    market_tone: str,
) -> Dict[str, Any]:
    bid = str(branch.get("branch_id") or "")
    tags = branch.get("collision_tags") or []

    outcome = "neutral"
    note = "주관·행동 가설 — 가격 방향만으로 판정 제한"

    if market_direction == "insufficient_data":
        return {"branch_id": bid, "outcome": "insufficient_data", "note": note}

    if bid == "expr_vs_cautious_market" and market_tone == "caution":
        if market_direction == "down":
            outcome = "aligned"
            note = "경계 톤 + 하락일 — 관측 우선 가설과 방향 일치(느슨)"
        elif market_direction == "up":
            outcome = "partial"
            note = "경계 톤 + 상승일 — 확장 자제 가설과 부분 충돌"
    elif bid == "reactive_pacing" and market_direction == "down":
        outcome = "partial"
        note = "별축·페이싱 + 하락 — 즉답 자제 가설 부분 정합"
    elif bid == "aligned_execution_hypo" and market_direction == "up":
        outcome = "partial"
        note = "균형·구조 가설 + 상승 — 실행 가설 느슨 정합"
    elif bid == "taeyang_overheat_guard" and market_direction == "up":
        outcome = "partial"
        note = "과열 경계 + 상승 — 보수 규모 가설 부분 정합"
    elif bid == "default_observe":
        outcome = "neutral"
        note = "fallback 분기 — 중립"

    return {"branch_id": bid, "outcome": outcome, "note": note, "collision_tags": tags}


def score_hypothesis_log(
    log_path: Path,
    *,
    kospi_csv: Path = DEFAULT_KOSPI,
) -> Dict[str, Any]:
    envelope = _read_json(log_path)
    stream = envelope.get("hypothesis_stream") or envelope
    cal = str(envelope.get("calendar_kst") or stream.get("calendar_kst") or "")
    ret, direction = _kospi_return_for_date(kospi_csv, cal)
    market_direction = direction if direction != "insufficient_data" else "insufficient_data"
    if ret is None and direction not in ("up", "down", "flat"):
        market_direction = "insufficient_data"

    branches_out: List[Dict[str, Any]] = []
    for br in stream.get("branches") or []:
        if isinstance(br, dict):
            branches_out.append(
                _score_branch(
                    br,
                    market_direction=market_direction,
                    market_tone=str(stream.get("market_tone") or "neutral"),
                )
            )

    aligned = sum(1 for b in branches_out if b.get("outcome") == "aligned")
    partial = sum(1 for b in branches_out if b.get("outcome") == "partial")

    return {
        "schema": "commander_hypothesis_branch_scores_v1",
        "hypothesis_tier": "B",
        "non_gating": True,
        "scored_at_utc": _utc_now(),
        "hypothesis_calendar_kst": cal,
        "log_path": str(log_path),
        "kospi_csv": str(kospi_csv),
        "market_return_pct": round(ret * 100, 4) if ret is not None else None,
        "market_direction": market_direction,
        "branch_scores": branches_out,
        "summary": {
            "n_branches": len(branches_out),
            "aligned": aligned,
            "partial": partial,
            "neutral": sum(1 for b in branches_out if b.get("outcome") == "neutral"),
        },
        "evolution_note": "P31d draft only — weights not auto-applied",
    }


def resolve_log_for_date(date_kst: str) -> Path:
    return LOG_DIR / f"{date_kst}_hypothesis_log_v1.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--date-kst",
        help="Hypothesis archive date (default: yesterday KST)",
    )
    ap.add_argument("--log-json", type=Path, default=None)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.log_json:
        log_path = args.log_json
    else:
        if args.date_kst:
            cal = args.date_kst
        else:
            yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
            cal = yesterday
        log_path = resolve_log_for_date(cal)

    if not log_path.is_file():
        raise SystemExit(f"missing log: {log_path}")

    doc = score_hypothesis_log(log_path, kospi_csv=args.kospi_csv)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"hypothesis_date={doc.get('hypothesis_calendar_kst')} direction={doc.get('market_direction')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
