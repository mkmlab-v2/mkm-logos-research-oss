#!/usr/bin/env python3
"""Align each news_observation row with the earliest direction_label_bar after as_of (calendar).

For each news row: pick the first label (filtered by instrument_id + horizon, sorted by
label_date) where label_date > date(as_of_utc). Matches the strict PIT rule used by
check_news_label_join_temporal_v1 (--strict-as-of-date-before-label-date).

Research-only; not a causal proof of correct modeling.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

JOIN_SCHEMA = "news_direction_join_v1"


def _parse_news_line(line: str) -> dict[str, Any]:
    return json.loads(line.strip())


def _as_of_date(row: dict[str, Any]) -> date:
    s = str(row["as_of_utc"]).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _label_date(row: dict[str, Any]) -> date:
    s = str(row["label_date"]).strip()
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = [ln for ln in path.read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    return [_parse_news_line(ln) for ln in lines]


def _filter_labels(
    labels: list[dict[str, Any]], instrument_id: str, horizon: str
) -> list[dict[str, Any]]:
    out = [
        r
        for r in labels
        if r.get("schema_version") == "direction_label_bar_v1"
        and str(r.get("instrument_id", "")).strip() == instrument_id
        and str(r.get("horizon", "")).strip() == horizon
    ]
    return sorted(out, key=lambda r: _label_date(r))


def _first_label_after(sorted_labels: list[dict[str, Any]], as_of_d: date) -> dict[str, Any] | None:
    for lb in sorted_labels:
        ld = _label_date(lb)
        if ld > as_of_d:
            return lb
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Walk-forward join: news_observation_v1 + direction_label_bar_v1"
    )
    ap.add_argument("--news-jsonl", type=Path, required=True)
    ap.add_argument("--labels-jsonl", type=Path, required=True)
    ap.add_argument("--instrument-id", type=str, required=True, help="e.g. KOSPI")
    ap.add_argument("--horizon", type=str, default="1d")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--strict-all",
        action="store_true",
        help="Exit 1 if any news row has no matching label after as_of.",
    )
    ap.add_argument(
        "--include-news",
        action="store_true",
        help="Embed full news row under key 'news'.",
    )
    ap.add_argument(
        "--include-label",
        action="store_true",
        help="Embed full label row under key 'label'.",
    )
    args = ap.parse_args()

    ins = str(args.instrument_id).strip()
    hz = str(args.horizon).strip().lower()
    if not hz.endswith(("d", "w")):
        hz = f"{hz}d"

    news_rows = _load_jsonl(Path(args.news_jsonl))
    all_labels = _load_jsonl(Path(args.labels_jsonl))
    pool = _filter_labels(all_labels, ins, hz)
    if not pool and args.strict_all:
        print("ERROR: no direction_label_bar rows for instrument/horizon", file=sys.stderr)
        return 1

    out_lines: list[str] = []
    missing = 0
    for nr in news_rows:
        if nr.get("schema_version") != "news_observation_v1":
            print("ERROR: expected news_observation_v1 row", file=sys.stderr)
            return 1
        aod = _as_of_date(nr)
        lb = _first_label_after(pool, aod)
        if lb is None:
            missing += 1
            if args.strict_all:
                print(
                    f"ERROR: no label after as_of={aod} for observation_id={nr.get('observation_id')}",
                    file=sys.stderr,
                )
                return 1
            continue
        rec: dict[str, Any] = {
            "schema_version": JOIN_SCHEMA,
            "observation_id": nr["observation_id"],
            "as_of_utc": nr["as_of_utc"],
            "text_sha256": nr["text_sha256"],
            "instrument_id": ins,
            "horizon": hz,
            "label_date": lb["label_date"],
            "direction": lb["direction"],
            "label_sha256": lb["label_sha256"],
        }
        if "neutral_bps" in lb:
            rec["neutral_bps"] = lb["neutral_bps"]
        if args.include_news:
            rec["news"] = nr
        if args.include_label:
            rec["label"] = lb
        out_lines.append(json.dumps(rec, ensure_ascii=False))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} joined={len(out_lines)} "
        f"skipped_no_label={missing} pool={len(pool)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
