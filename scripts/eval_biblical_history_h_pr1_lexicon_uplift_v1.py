#!/usr/bin/env python3
"""H-PR1 platform/disinformation lexicon uplift: stress vs control windows (B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HYP = ROOT / "docs/final/artifacts/biblical_resonance_hypotheses_v1.json"
DEFAULT_FIXTURE = ROOT / "tests/fixtures/biblical_resonance_research_news_smoke_v1.jsonl"
DEFAULT_RESEARCH_SLICE = ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl"
DEFAULT_PRODUCTION = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/biblical_history_h_pr1_lexicon_uplift_latest.json"

PLATFORM_STRESS_WINDOW = ("2016-01-01T00:00:00Z", "2020-12-31T23:59:59Z")
PLATFORM_CONTROL_WINDOW = ("2014-01-01T00:00:00Z", "2015-12-31T23:59:59Z")
RESEARCH_STRESS_WINDOW = ("2026-05-01T00:00:00Z", "2026-06-30T23:59:59Z")
RESEARCH_CONTROL_WINDOW = ("2026-03-01T00:00:00Z", "2026-04-30T23:59:59Z")


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
    stress_start: datetime,
    stress_end: datetime,
    control_start: datetime,
    control_end: datetime,
) -> dict[str, Any]:
    rows = _load_jsonl(path)
    stress = _window_stats(rows, groups, stress_start, stress_end)
    control = _window_stats(rows, groups, control_start, control_end)
    uplift = stress["match_ratio"] - control["match_ratio"]
    return {
        "corpus": label,
        "path": str(path),
        "stress_window": stress,
        "control_window": control,
        "uplift_match_ratio": round(uplift, 6),
        "uplift_positive": uplift > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="H-PR1 platform lexicon uplift (stress vs control).")
    ap.add_argument("--hypotheses-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--fixture-jsonl", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--research-slice-jsonl", type=Path, default=DEFAULT_RESEARCH_SLICE)
    ap.add_argument("--production-jsonl", type=Path, default=DEFAULT_PRODUCTION)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    hyp_doc = _load_json(args.hypotheses_json)
    pr1 = next(
        (h for h in hyp_doc.get("hypotheses", []) if isinstance(h, dict) and h.get("id") == "H-PR1"),
        None,
    )
    if not pr1:
        raise SystemExit("H-PR1 not found in hypotheses json")
    groups = pr1.get("keyword_groups_any", [])
    if not isinstance(groups, list):
        groups = []

    windows = {
        "research_2026_anchor": (RESEARCH_STRESS_WINDOW, RESEARCH_CONTROL_WINDOW),
        "historical_platform_era": (PLATFORM_STRESS_WINDOW, PLATFORM_CONTROL_WINDOW),
    }
    parsed: dict[str, tuple[datetime, datetime, datetime, datetime]] = {}
    for name, (stress, control) in windows.items():
        ss, se = _parse_iso(stress[0]), _parse_iso(stress[1])
        cs, ce = _parse_iso(control[0]), _parse_iso(control[1])
        if not all([ss, se, cs, ce]):
            raise SystemExit(f"invalid window constants for {name}")
        parsed[name] = (ss, se, cs, ce)

    corpora_research = [
        _eval_corpus("smoke_fixture_2026", args.fixture_jsonl, groups, *parsed["research_2026_anchor"]),
        _eval_corpus("research_slice_2026", args.research_slice_jsonl, groups, *parsed["research_2026_anchor"]),
        _eval_corpus("production_news_2026", args.production_jsonl, groups, *parsed["research_2026_anchor"]),
    ]

    payload = {
        "schema": "biblical_history_h_pr1_lexicon_uplift_v1",
        "hypothesis_id": "H-PR1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "windows": {
            "research_2026_anchor": {
                "stress": list(RESEARCH_STRESS_WINDOW),
                "control": list(RESEARCH_CONTROL_WINDOW),
            },
            "historical_platform_era": {
                "stress": list(PLATFORM_STRESS_WINDOW),
                "control": list(PLATFORM_CONTROL_WINDOW),
            },
        },
        "keyword_groups_any": groups,
        "corpora_research_2026_anchor": corpora_research,
        "summary": {
            "smoke_2026_uplift_positive": corpora_research[0]["uplift_positive"],
            "smoke_2026_stress_match_ratio": corpora_research[0]["stress_window"]["match_ratio"],
            "research_slice_2026_stress_rows": corpora_research[1]["stress_window"]["row_count"],
            "production_2026_stress_rows": corpora_research[2]["stress_window"]["row_count"],
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "Platform-era windows are historiography anchors; 2026 windows align research smoke and Korea ingest.",
        },
        "fact_lock_notice": "Lexicon coverage only; not price-direction or Track A gate.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
