#!/usr/bin/env python3
"""Evening scorecard — morning advanced briefing predictions vs market close [HYPO].

Feeds commander_briefing_evolution rail (dry-run).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
KST = ZoneInfo("Asia/Seoul")
BRIEFING_LOG = ROOT / "reports" / "briefing_log"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "commander_evening_briefing_score_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _market_close_direction(csv_path: Path, date_kst: str) -> Tuple[Optional[float], str]:
    from scripts.score_commander_hypothesis_branches_v1 import _kospi_return_for_date  # noqa: WPS433

    ret, direction = _kospi_return_for_date(csv_path, date_kst)
    if direction in ("up", "down", "flat"):
        return ret, direction
    return ret, "insufficient_data"


def _score_prediction(
    pred: Dict[str, Any],
    *,
    market_direction: str,
) -> Dict[str, Any]:
    pid = pred.get("prediction_id")
    kind = pred.get("kind")
    outcome = "not_scored"
    note = ""

    if market_direction == "insufficient_data":
        return {**pred, "outcome": "insufficient_data", "note": "KOSPI CSV에 해당일 없음"}

    proxy = str(pred.get("direction_proxy") or "").upper()
    if kind == "market_direction_hypo" and proxy:
        if proxy in ("WATCH", "HOLD", "CAUTION", "REDUCE") and market_direction == "down":
            outcome, note = "aligned", "경계 액션 + 하락일"
        elif proxy in ("GO", "TILT_UP", "BUY") and market_direction == "up":
            outcome, note = "aligned", "우위 액션 + 상승일"
        elif proxy in ("WATCH", "HOLD") and market_direction == "flat":
            outcome, note = "partial", "횡보·관측"
        else:
            outcome, note = "partial", "액션 라벨 vs 종가 방향 느슨 대조"
    elif kind == "btrack_price_hypo":
        d = str(pred.get("direction_proxy") or "").lower()
        if d in ("bull", "up") and market_direction == "up":
            outcome, note = "aligned", "상승 가설"
        elif d in ("bear", "down") and market_direction == "down":
            outcome, note = "aligned", "하락 가설"
        elif d in ("neutral", "flat") and market_direction == "flat":
            outcome, note = "partial", "중립"
        else:
            outcome, note = "reject", "방향 불일치"
    elif kind in ("behavioral_hypothesis", "narrative_hypothesis"):
        if market_direction == "down":
            outcome, note = "partial", "행동가설 — 하락일 관측·페이싱 가설과 느슨 정합"
        else:
            outcome, note = "neutral", "행동가설 — 가격만으로 판정 제한"

    return {
        "prediction_id": pid,
        "kind": kind,
        "outcome": outcome,
        "note": note,
        "market_direction": market_direction,
    }


def score_evening_briefing(
    archive_path: Path,
    *,
    kospi_csv: Path = DEFAULT_KOSPI,
) -> Dict[str, Any]:
    from scripts.multi_asset_market_adapter_v1 import (  # noqa: WPS433
        build_evening_asset_panel,
        score_prediction_multi_asset,
    )

    env = _read_json(archive_path)
    briefing = env.get("briefing") or env
    cal = str(env.get("calendar_kst") or briefing.get("calendar_kst") or "")
    morning_seal = briefing.get("market_seal")
    assets = build_evening_asset_panel(cal, morning_seal=morning_seal)
    kospi = assets.get("kospi") or {}
    ret_pct = kospi.get("return_pct")
    mdir = str(kospi.get("direction") or "insufficient_data")

    scored: List[Dict[str, Any]] = []
    for pred in briefing.get("predictions") or []:
        if isinstance(pred, dict):
            scored.append(score_prediction_multi_asset(pred, assets=assets))

    counts = {k: 0 for k in ("aligned", "partial", "reject", "neutral", "not_scored", "insufficient_data", "pending_until_morning")}
    for s in scored:
        o = s.get("outcome") or "not_scored"
        counts[o] = counts.get(o, 0) + 1

    n_scorable = sum(counts[k] for k in ("aligned", "partial", "reject", "neutral"))
    hit_rate = (counts["aligned"] + 0.5 * counts["partial"]) / n_scorable if n_scorable else None

    return {
        "schema": "commander_evening_briefing_score_v2",
        "hypothesis_tier": "B",
        "non_gating": True,
        "scored_at_utc": _utc_now(),
        "calendar_kst": cal,
        "briefing_id": briefing.get("briefing_id"),
        "archive_path": str(archive_path),
        "multi_asset": assets,
        "market_return_pct": ret_pct,
        "market_direction": mdir,
        "prediction_scores": scored,
        "summary": {
            **counts,
            "n_predictions": len(scored),
            "soft_hit_rate": round(hit_rate, 4) if hit_rate is not None else None,
            "nasdaq_pending": counts.get("pending_until_morning", 0),
        },
        "evolution_eligible": mdir != "insufficient_data",
    }


def resolve_archive(date_kst: str) -> Path:
    return BRIEFING_LOG / f"{date_kst}_morning_briefing_v1.json"


def build_evening_telegram(score: Dict[str, Any]) -> str:
    sm = score.get("summary") or {}
    ma = score.get("multi_asset") or {}
    lines = [
        f"🌙 MKM 저녁 브리핑 채점 · {score.get('calendar_kst')}",
        f"briefing_id={score.get('briefing_id')} · KOSPI {score.get('market_direction')} "
        f"({score.get('market_return_pct')}%)",
        f"BTC {((ma.get('btc') or {}).get('direction'))} "
        f"({((ma.get('btc') or {}).get('return_pct'))}%) · "
        f"NASDAQ {((ma.get('nasdaq') or {}).get('direction'))}",
        f"soft_hit_rate={sm.get('soft_hit_rate')} · aligned={sm.get('aligned')} partial={sm.get('partial')} "
        f"reject={sm.get('reject')} nasdaq_pending={sm.get('nasdaq_pending')}",
        "",
        "▸ 예측별",
    ]
    for s in score.get("prediction_scores") or []:
        lines.append(f"  · {s.get('prediction_id')}: {s.get('outcome')} — {s.get('note','')[:80]}")
    lines.extend(
        [
            "",
            "[HYPO] 자율진화는 run_commander_briefing_evolution_v1 · 실매매 없음",
        ]
    )
    return "\n".join(lines)


def _refresh_market_csvs(workspace: Path = ROOT) -> Dict[str, Any]:
    """Optional head step — YFinance CSV refresh before score."""
    import subprocess

    results: Dict[str, Any] = {}
    for name in ("fetch_kospi_yfinance_csv.py", "fetch_btc_yfinance_csv.py", "fetch_nasdaq_yfinance_csv.py"):
        script = workspace / "scripts" / name
        if not script.is_file():
            results[name] = {"ok": False, "reason": "missing"}
            continue
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        results[name] = {"ok": proc.returncode == 0, "exit_code": proc.returncode}
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-kospi-fetch", action="store_true", help="Skip all YFinance CSV refresh")
    ap.add_argument("--date-kst", default="", help="Morning briefing date (default: today KST)")
    ap.add_argument("--archive-json", type=Path, default=None)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-telegram-json", action="store_true")
    args = ap.parse_args()

    if args.archive_json:
        path = args.archive_json
    else:
        cal = args.date_kst or datetime.now(KST).strftime("%Y-%m-%d")
        path = resolve_archive(cal)

    if not path.is_file():
        raise SystemExit(f"missing archive: {path}")

    if not args.skip_kospi_fetch:
        fetches = _refresh_market_csvs()
        for name, st in fetches.items():
            if not st.get("ok"):
                print(f"WARN: {name} exit={st.get('exit_code')}", file=sys.stderr)

    doc = score_evening_briefing(path, kospi_csv=args.kospi_csv)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_dir = ROOT / "reports" / "briefing_log"
    cal = doc.get("calendar_kst")
    if cal:
        evening_path = log_dir / f"{cal}_evening_score_v1.json"
        evening_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_telegram_json:
        tg_path = ROOT / "reports" / "commander_evening_telegram_preview_latest.json"
        tg_path.write_text(
            json.dumps({"text": build_evening_telegram(doc)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"WROTE: {args.out_json} soft_hit={doc.get('summary',{}).get('soft_hit_rate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
