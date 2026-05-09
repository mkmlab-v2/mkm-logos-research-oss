#!/usr/bin/env python3
"""Build daily falsification input from lens snapshots and KOSPI latest return."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
RESEARCH = ROOT / "research" / "market_data"
REPORTS = ROOT / "reports"

DEFAULT_KOSPI_CSV = RESEARCH / "kospi_daily_external_yf.csv"
DEFAULT_OUT = REPORTS / "daily_execution_falsification_input_latest.json"
DEFAULT_MYEONGNI = ART / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ART / "sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ART / "logos_independent_lens_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _label_from_score(score: float | None, eps: float = 0.05) -> str:
    if score is None:
        return "UNKNOWN"
    if score > eps:
        return "UP"
    if score < -eps:
        return "DOWN"
    return "NEUTRAL"


def _float_opt(v: Any) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _read_latest_kospi_return(csv_path: Path) -> tuple[str | None, float | None]:
    if not csv_path.is_file():
        return None, None
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        rows = [r for r in reader if isinstance(r, dict)]
    if len(rows) < 2:
        return None, None

    def pick(row: dict[str, str], keys: list[str]) -> str | None:
        for k in keys:
            if k in row and str(row[k]).strip():
                return str(row[k]).strip()
        return None

    valid: list[tuple[str | None, float]] = []
    for row in reversed(rows):
        close = _float_opt(pick(row, ["Close", "close", "Adj Close", "adj_close", "종가"]))
        if close is None:
            continue
        date_val = pick(row, ["Date", "date", "날짜"])
        valid.append((date_val, close))
        if len(valid) >= 2:
            break

    if len(valid) < 2:
        latest_date = valid[0][0] if valid else None
        return latest_date, None

    latest_date, latest_close = valid[0]
    prev_close = valid[1][1]
    return latest_date, latest_close - prev_close


def _lens_score(doc: dict[str, Any]) -> float | None:
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    return _float_opt(scores.get("direction_score"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang-json", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos-json", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    myeongni = _read_json(args.myeongni_json)
    sasang = _read_json(args.sasang_json)
    logos = _read_json(args.logos_json)

    date_val, ret = _read_latest_kospi_return(args.kospi_csv)
    actual_label = _label_from_score(ret, eps=0.0) if ret is not None else "UNKNOWN"

    entries: list[dict[str, Any]] = []
    for lens_id, doc in (
        ("myeongni", myeongni),
        ("sasang", sasang),
        ("logos", logos),
    ):
        if not doc:
            continue
        score = _lens_score(doc)
        entries.append(
            {
                "lens_id": lens_id,
                "prediction_label": _label_from_score(score),
                "actual_label": actual_label,
                "meta": {
                    "direction_score": score,
                    "source_json": str((args.myeongni_json if lens_id == "myeongni" else args.sasang_json if lens_id == "sasang" else args.logos_json).resolve()).replace("\\", "/"),
                },
            }
        )

    payload = {
        "schema": "daily_execution_falsification_input_v1",
        "generated_at_utc": _now(),
        "date_utc": str(date_val or datetime.now(timezone.utc).date().isoformat()),
        "source": "auto_lens_kospi_latest_return_v1",
        "market_snapshot": {
            "kospi_csv": str(args.kospi_csv.resolve()).replace("\\", "/"),
            "latest_daily_return": ret,
            "actual_label": actual_label,
        },
        "entries": entries,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"entries={len(entries)}; actual_label={actual_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
