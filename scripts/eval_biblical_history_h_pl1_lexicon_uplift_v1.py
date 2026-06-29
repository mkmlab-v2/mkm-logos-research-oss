#!/usr/bin/env python3
"""H-PL1 plague lexicon uplift: COVID window vs control (B-track, research only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYP = ROOT / "docs/final/artifacts/biblical_resonance_hypotheses_v1.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/biblical_resonance_covid_window_news_smoke_v1.jsonl"
DEFAULT_RESEARCH_SLICE = ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl"
DEFAULT_PRODUCTION = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/biblical_history_h_pl1_lexicon_uplift_latest.json"

HISTORICAL_COVID_WINDOW = ("2020-03-01T00:00:00Z", "2020-03-31T23:59:59Z")
HISTORICAL_CONTROL_WINDOW = ("2020-01-01T00:00:00Z", "2020-02-29T23:59:59Z")
RESEARCH_COVID_WINDOW = ("2026-06-01T00:00:00Z", "2026-06-30T23:59:59Z")
RESEARCH_CONTROL_WINDOW = ("2026-05-01T00:00:00Z", "2026-05-31T23:59:59Z")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def _in_range(ts: datetime | None, start: datetime, end: datetime) -> bool:
    return ts is not None and start <= ts <= end


def _group_match(text: str, group: list[str]) -> bool:
    return any(tok.lower() in text for tok in group)


def _hypothesis_match(text: str, groups: list[list[str]]) -> bool:
    return any(_group_match(text, g) for g in groups)


def _window_stats(
    rows: list[dict[str, Any]],
    groups: list[list[str]],
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    window_rows: list[dict[str, Any]] = []
    matched = 0
    for row in rows:
        ts = _parse_iso(row.get("as_of_utc") or row.get("published_utc"))
        if not _in_range(ts, start, end):
            continue
        window_rows.append(row)
        txt = str(row.get("canonical_text", "")).lower()
        if _hypothesis_match(txt, groups):
            matched += 1
    total = len(window_rows)
    ratio = (matched / total) if total else 0.0
    return {
        "row_count": total,
        "matched_rows": matched,
        "match_ratio": round(ratio, 6),
    }


def _eval_corpus(
    label: str,
    path: Path,
    groups: list[list[str]],
    covid_start: datetime,
    covid_end: datetime,
    control_start: datetime,
    control_end: datetime,
) -> dict[str, Any]:
    rows = _load_jsonl(path)
    covid = _window_stats(rows, groups, covid_start, covid_end)
    control = _window_stats(rows, groups, control_start, control_end)
    uplift = covid["match_ratio"] - control["match_ratio"]
    return {
        "corpus": label,
        "path": str(path),
        "covid_window": covid,
        "control_window": control,
        "uplift_match_ratio": round(uplift, 6),
        "uplift_positive": uplift > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="H-PL1 plague lexicon uplift (COVID vs control window).")
    ap.add_argument("--hypotheses-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--fixture-jsonl", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--research-slice-jsonl", type=Path, default=DEFAULT_RESEARCH_SLICE)
    ap.add_argument("--production-jsonl", type=Path, default=DEFAULT_PRODUCTION)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    hyp_doc = _load_json(args.hypotheses_json)
    pl1 = next(
        (h for h in hyp_doc.get("hypotheses", []) if isinstance(h, dict) and h.get("id") == "H-PL1"),
        None,
    )
    if not pl1:
        raise SystemExit("H-PL1 not found in hypotheses json")
    groups = pl1.get("keyword_groups_any", [])
    if not isinstance(groups, list):
        groups = []

    hist_covid_start = _parse_iso(HISTORICAL_COVID_WINDOW[0])
    hist_covid_end = _parse_iso(HISTORICAL_COVID_WINDOW[1])
    hist_control_start = _parse_iso(HISTORICAL_CONTROL_WINDOW[0])
    hist_control_end = _parse_iso(HISTORICAL_CONTROL_WINDOW[1])
    res_covid_start = _parse_iso(RESEARCH_COVID_WINDOW[0])
    res_covid_end = _parse_iso(RESEARCH_COVID_WINDOW[1])
    res_control_start = _parse_iso(RESEARCH_CONTROL_WINDOW[0])
    res_control_end = _parse_iso(RESEARCH_CONTROL_WINDOW[1])
    if not all(
        [
            hist_covid_start,
            hist_covid_end,
            hist_control_start,
            hist_control_end,
            res_covid_start,
            res_covid_end,
            res_control_start,
            res_control_end,
        ]
    ):
        raise SystemExit("invalid window constants")

    corpora_research = [
        _eval_corpus(
            "covid_fixture_smoke_2026_anchor",
            args.fixture_jsonl,
            groups,
            res_covid_start,
            res_covid_end,
            res_control_start,
            res_control_end,
        ),
        _eval_corpus(
            "research_slice_2026_anchor",
            args.research_slice_jsonl,
            groups,
            res_covid_start,
            res_covid_end,
            res_control_start,
            res_control_end,
        ),
        _eval_corpus(
            "production_news_2026_anchor",
            args.production_jsonl,
            groups,
            res_covid_start,
            res_covid_end,
            res_control_start,
            res_control_end,
        ),
    ]
    corpora_historical = [
        _eval_corpus(
            "covid_fixture_smoke_historical_2020",
            args.fixture_jsonl,
            groups,
            hist_covid_start,
            hist_covid_end,
            hist_control_start,
            hist_control_end,
        ),
    ]

    fixture_uplift = corpora_research[0]["uplift_match_ratio"]
    payload = {
        "schema": "biblical_history_h_pl1_lexicon_uplift_v1",
        "hypothesis_id": "H-PL1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "linked_question_id": "hist.health.who_covid_pheic_jan2020",
        "windows": {
            "research_2026_anchor": {
                "covid": list(RESEARCH_COVID_WINDOW),
                "control": list(RESEARCH_CONTROL_WINDOW),
            },
            "historical_2020_holdout": {
                "covid": list(HISTORICAL_COVID_WINDOW),
                "control": list(HISTORICAL_CONTROL_WINDOW),
            },
        },
        "keyword_groups_any": groups,
        "corpora_research_2026_anchor": corpora_research,
        "corpora_historical_2020": corpora_historical,
        "summary": {
            "fixture_2026_uplift_positive": fixture_uplift > 0,
            "fixture_2026_covid_window_match_ratio": corpora_research[0]["covid_window"]["match_ratio"],
            "fixture_2026_control_window_match_ratio": corpora_research[0]["control_window"]["match_ratio"],
            "research_slice_2026_covid_window_rows": corpora_research[1]["covid_window"]["row_count"],
            "production_2026_covid_window_rows": corpora_research[2]["covid_window"]["row_count"],
            "historical_2020_fixture_rows_in_window": corpora_historical[0]["covid_window"]["row_count"],
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": (
                "Fixture uses 2026 date anchor for lookback alignment; historical_event_ref "
                "still points to hist.health.who_covid_pheic_jan2020."
            ),
        },
        "fact_lock_notice": "Narrative lexicon only; not clinical prediction or price-direction gate.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
