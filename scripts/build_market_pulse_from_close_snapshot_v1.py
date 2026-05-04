#!/usr/bin/env python3
"""Build market_pulse_v1 JSON from close snapshot text/JSON.

Priority:
1) explicit CLI overrides
2) JSON input fields
3) text parsing (Korean close snapshot blocks)
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        if isinstance(v, str):
            vv = v.replace(",", "").strip()
            if not vv:
                return None
            return float(vv)
        return float(v)
    except (TypeError, ValueError):
        return None


def _extract_number(text: str, pattern: str) -> float | None:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    return _to_float(m.group(1))


def _extract_pair_counts(text: str) -> tuple[float | None, float | None]:
    up = _extract_number(text, r"상승종목수\s*([0-9,]+)")
    down = _extract_number(text, r"하락종목수\s*([0-9,]+)")
    return up, down


def _extract_flow(text: str) -> tuple[float | None, float | None]:
    # Expects units in 억원 like: 외국인 +29,308 억원 / 기관 +20,098 억원
    foreign = _extract_number(text, r"외국인\s*([+-]?[0-9,]+)\s*억원")
    institution = _extract_number(text, r"기관\s*([+-]?[0-9,]+)\s*억원")
    return foreign, institution


def _extract_theme_returns(text: str) -> list[float]:
    vals = re.findall(r"(?:\+)?([0-9]{1,2}\.[0-9]{1,2})%", text)
    out: list[float] = []
    for v in vals[:20]:
        fv = _to_float(v)
        if fv is not None:
            out.append(float(fv))
    return out


def _derive_theme_score(returns: list[float]) -> float | None:
    if not returns:
        return None
    top3 = sorted(returns, reverse=True)[:3]
    avg_top = sum(top3) / len(top3)
    # 5% -> 0.3, 10% -> 0.7, >=20% -> 1.0
    score = (avg_top - 2.0) / 12.0
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0
    return round(score, 4)


def _build_from_json(doc: dict[str, Any]) -> dict[str, float | None]:
    return {
        "advance_decline_ratio": _to_float(doc.get("advance_decline_ratio")),
        "foreign_net_buy_krw_eok": _to_float(doc.get("foreign_net_buy_krw_eok")),
        "institution_net_buy_krw_eok": _to_float(doc.get("institution_net_buy_krw_eok")),
        "theme_leadership_score": _to_float(doc.get("theme_leadership_score")),
    }


def _build_from_text(text: str) -> dict[str, float | None]:
    up, down = _extract_pair_counts(text)
    breadth: float | None = None
    if up is not None and down is not None and down > 0:
        breadth = round(float(up) / float(down), 4)
    foreign, institution = _extract_flow(text)
    score = _derive_theme_score(_extract_theme_returns(text))
    return {
        "advance_decline_ratio": breadth,
        "foreign_net_buy_krw_eok": foreign,
        "institution_net_buy_krw_eok": institution,
        "theme_leadership_score": score,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build market_pulse_v1 from close snapshot.")
    ap.add_argument("--input-json", default="", help="Optional source JSON path.")
    ap.add_argument("--input-text", default="", help="Optional source text path.")
    ap.add_argument("--out", required=True, help="Output market pulse JSON path.")
    ap.add_argument("--source", default="close_snapshot_parser_v1")
    ap.add_argument("--updated-at-utc", default="")
    ap.add_argument("--advance-decline-ratio", type=float, default=None)
    ap.add_argument("--foreign-net-buy-krw-eok", type=float, default=None)
    ap.add_argument("--institution-net-buy-krw-eok", type=float, default=None)
    ap.add_argument("--theme-leadership-score", type=float, default=None)
    args = ap.parse_args()

    merged: dict[str, float | None] = {
        "advance_decline_ratio": None,
        "foreign_net_buy_krw_eok": None,
        "institution_net_buy_krw_eok": None,
        "theme_leadership_score": None,
    }

    in_json = str(args.input_json or "").strip()
    if in_json:
        doc = json.loads(Path(in_json).read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise SystemExit("input-json must be object JSON.")
        for k, v in _build_from_json(doc).items():
            if v is not None:
                merged[k] = v

    in_text = str(args.input_text or "").strip()
    if in_text:
        text = Path(in_text).read_text(encoding="utf-8")
        for k, v in _build_from_text(text).items():
            if v is not None:
                merged[k] = v

    cli_overrides = {
        "advance_decline_ratio": args.advance_decline_ratio,
        "foreign_net_buy_krw_eok": args.foreign_net_buy_krw_eok,
        "institution_net_buy_krw_eok": args.institution_net_buy_krw_eok,
        "theme_leadership_score": args.theme_leadership_score,
    }
    for k, v in cli_overrides.items():
        if v is not None:
            merged[k] = float(v)

    missing = [k for k, v in merged.items() if v is None]
    if missing:
        raise SystemExit(f"missing required market_pulse fields: {', '.join(missing)}")

    updated_at_utc = str(args.updated_at_utc or "").strip()
    if not updated_at_utc:
        updated_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    out_doc = {
        "schema": "market_pulse_v1",
        "source": str(args.source or "close_snapshot_parser_v1"),
        "updated_at_utc": updated_at_utc,
        "advance_decline_ratio": round(float(merged["advance_decline_ratio"]), 6),
        "foreign_net_buy_krw_eok": float(merged["foreign_net_buy_krw_eok"]),
        "institution_net_buy_krw_eok": float(merged["institution_net_buy_krw_eok"]),
        "theme_leadership_score": round(float(merged["theme_leadership_score"]), 6),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

