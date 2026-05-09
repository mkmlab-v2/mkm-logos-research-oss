#!/usr/bin/env python3
"""Generate a one-line KOSPI daily log with rule-based judgment.

Rule set (from report):
- Risk-On:  F1 > +10000 and F2 > +5000 and B1 >= 0.52
- Risk-Off: F1 < -10000 and B1 <= 0.45
            OR (V1 is HIGH and F1 < 0)
- Neutral:  otherwise
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate KOSPI daily one-line execution log."
    )
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format.")
    parser.add_argument("--f1", required=True, type=float, help="Foreigner net flow.")
    parser.add_argument("--f2", required=True, type=float, help="Program net flow.")
    parser.add_argument("--b1", required=True, type=float, help="Market breadth ratio.")
    parser.add_argument(
        "--v1",
        required=True,
        choices=["LOW", "MID", "HIGH"],
        help="Volatility state.",
    )
    parser.add_argument(
        "--action",
        default="관망",
        help="Action label (e.g. 분할진입, 관망, 비중축소).",
    )
    parser.add_argument(
        "--next-day-ret",
        default="?",
        choices=["+", "-", "0", "?"],
        help="Next day return sign.",
    )
    parser.add_argument(
        "--vol-expand",
        default="?",
        choices=["Y", "N", "?"],
        help="Whether volatility expanded.",
    )
    parser.add_argument("--note", default="-", help="Short note.")
    parser.add_argument(
        "--append-path",
        help="If provided, append generated line to this file.",
    )
    return parser.parse_args()


def judge(f1: float, f2: float, b1: float, v1: str) -> str:
    if f1 > 10000 and f2 > 5000 and b1 >= 0.52:
        return "Risk-On"
    if (f1 < -10000 and b1 <= 0.45) or (v1 == "HIGH" and f1 < 0):
        return "Risk-Off"
    return "Neutral"


def validate_date(date_text: str) -> None:
    datetime.strptime(date_text, "%Y-%m-%d")


def build_line(
    date: str,
    f1: float,
    f2: float,
    b1: float,
    v1: str,
    judgment: str,
    action: str,
    next_day_ret: str,
    vol_expand: str,
    note: str,
) -> str:
    return (
        f"[DATE={date}] "
        f"[F1={f1:.0f}] "
        f"[F2={f2:.0f}] "
        f"[B1={b1:.3f}] "
        f"[V1={v1}] "
        f"[JUDGMENT={judgment}] "
        f"[ACTION={action}] "
        f"[NEXT_DAY_RET={next_day_ret}] "
        f"[VOL_EXPAND={vol_expand}] "
        f"[NOTE={note}]"
    )


def main() -> int:
    args = parse_args()
    validate_date(args.date)
    judgment = judge(args.f1, args.f2, args.b1, args.v1)
    line = build_line(
        date=args.date,
        f1=args.f1,
        f2=args.f2,
        b1=args.b1,
        v1=args.v1,
        judgment=judgment,
        action=args.action,
        next_day_ret=args.next_day_ret,
        vol_expand=args.vol_expand,
        note=args.note,
    )
    print(line)

    if args.append_path:
        path = Path(args.append_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(f"Appended to: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

