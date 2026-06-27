# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.6}
# Balance: 92
# Purpose: Build 30-year validation guard artifact for lens combo backtest.
# Keywords: backtest, 30y, guard, artifacts, governance
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

BACKTEST_V1 = ART / "prophecy_lens_combo_backtest_v1_latest.json"
BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
OUT = ART / "prophecy_lens_combo_backtest_30y_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _date_range_and_years(csv_path: Path) -> tuple[str | None, str | None, int, float]:
    if not csv_path.is_file():
        return None, None, 0, 0.0
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    if not rows:
        return None, None, 0, 0.0
    start = str(rows[0].get("Date") or rows[0].get("date") or "")[:10] or None
    end = str(rows[-1].get("Date") or rows[-1].get("date") or "")[:10] or None
    if not start or not end:
        return start, end, len(rows), 0.0
    try:
        ds = datetime.fromisoformat(start).date()
        de = datetime.fromisoformat(end).date()
        years = max(0.0, (de - ds).days / 365.25)
    except ValueError:
        years = 0.0
    return start, end, len(rows), round(years, 4)


def main() -> int:
    backtest = _load_json(BACKTEST_V1) if BACKTEST_V1.is_file() else {}
    start, end, rows, years = _date_range_and_years(BTC_CSV)
    has_30y = years >= 30.0

    payload: dict[str, Any] = {
        "schema": "prophecy_lens_combo_backtest_30y_guard_v1",
        "artifact_display_name": "prophecy_lens_combo_backtest_long_horizon_guard",
        "artifact_display_name_ko": "예언 렌즈 콤보 장기 구간 가드 (BTC CSV 기준 — KOSPI 30년 아님)",
        "instrument_scope": "BTC_daily_csv_only",
        "do_not_confuse_ko": (
            "파일명의 30y는 BTC 일봉 CSV 가용 연수 가드이며, "
            "KOSPI multilens 30년 백테스트와 혼동 금지."
        ),
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "source_backtest_v1_json": str(BACKTEST_V1),
        "source_btc_csv": str(BTC_CSV),
        "coverage": {
            "csv_date_start": start,
            "csv_date_end": end,
            "csv_row_count": rows,
            "available_years": years,
            "required_years_for_30y_claim": 30.0,
            "has_required_30y_history": has_30y,
        },
        "thirty_year_claim_gate": {
            "status": "PROVEN_30Y_SCOPE" if has_30y else "INSUFFICIENT_HISTORY_HOLD",
            "allow_30y_generalization": has_30y,
            "reason": "enough_history" if has_30y else "available_history_below_30y_threshold",
        },
        "best_strategy_snapshot_from_v1": backtest.get("best_strategy"),
        "note": "This artifact guards long-horizon claims. Missing/insufficient horizon must be treated as NOT_PROVEN for 30y statements.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"30Y_STATUS={payload['thirty_year_claim_gate']['status']} available_years={years}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
