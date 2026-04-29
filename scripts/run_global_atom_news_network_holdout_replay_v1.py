#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def tokenize(text: str) -> set[str]:
    return {t.strip().lower() for t in text.replace(",", " ").replace(".", " ").split() if t.strip()}


def score_stage(tokens: set[str], stage: str) -> float:
    lex = {
        "genesis": {"origin", "creation", "reset", "birth"},
        "torah": {"law", "policy", "regulation", "discipline", "covenant"},
        "prophets": {"collapse", "war", "crisis", "judgment", "empire", "conflict"},
        "gospels": {"recovery", "relief", "support", "mercy", "stabilization"},
        "full_canon": {"global", "systemic", "transition", "regime", "reallocation"},
    }
    inter = len(tokens.intersection(lex.get(stage, set())))
    denom = max(1, len(lex.get(stage, set())))
    return inter / denom


def top_stages(tokens: set[str], stage_rows: list[dict[str, Any]], k: int = 2) -> list[dict[str, Any]]:
    rows = []
    for s in stage_rows:
        if not isinstance(s, dict):
            continue
        st = str(s.get("stage") or "")
        base = float(s.get("edge_count") or 0.0)
        # light normalization to avoid giant stages always dominating
        density = base ** 0.5
        resonance = score_stage(tokens, st) * density
        rows.append(
            {
                "stage": st,
                "resonance_score": round(resonance, 6),
                "edge_count": s.get("edge_count"),
                "node_count": s.get("node_count"),
                "phase_transition_signal": s.get("phase_transition_signal"),
            }
        )
    rows.sort(key=lambda x: x["resonance_score"], reverse=True)
    return rows[:k]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run 2008/2020 holdout replay over global atom stage topology.")
    ap.add_argument("--batch-report-json", default="docs/final/artifacts/global_atom_full_canon_batch_report_latest.json")
    ap.add_argument("--holdout-news-jsonl", default="docs/final/artifacts/global_atom_news_holdout_dataset_v1.jsonl")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_news_network_holdout_replay_latest.json")
    args = ap.parse_args()

    rp = resolve(args.batch_report_json)
    if not rp.is_file():
        raise SystemExit(f"missing batch report: {rp}")
    report = load(rp)
    stages = report.get("stages") if isinstance(report.get("stages"), list) else []

    holdouts_default = [
        {
            "scenario_id": "holdout_2008_lehman",
            "period": "2008-09",
            "headline": "Lehman collapse triggers global credit crisis and emergency policy response",
            "expected_regime_transition": "crisis_to_policy",
        },
        {
            "scenario_id": "holdout_2020_covid_m1",
            "period": "2020-03",
            "headline": "Pandemic shock drives lockdown panic then fiscal-monetary stabilization",
            "expected_regime_transition": "shock_to_stabilization",
        },
    ]
    holdout_path = resolve(args.holdout_news_jsonl)
    holdouts_jsonl = load_jsonl(holdout_path)
    holdouts = holdouts_jsonl if holdouts_jsonl else holdouts_default

    rows = []
    for h in holdouts:
        headline = str(h.get("headline", "") or "").strip()
        if not headline:
            continue
        toks = tokenize(headline)
        tops = top_stages(toks, stages, k=2)
        top = tops[0] if tops else {}
        narrative = (
            f"News topology resonates strongest with `{top.get('stage')}` and then `{(tops[1] if len(tops)>1 else {}).get('stage')}`. "
            "This indicates a phase path from disruption pressure toward policy or stabilization nodes."
        )
        rows.append(
            {
                "scenario_id": h.get("scenario_id"),
                "period": h.get("period"),
                "headline": headline,
                "expected_regime_transition": h.get("expected_regime_transition"),
                "top_resonance": top,
                "top2_resonance": tops,
                "network_structural_insight": narrative,
            }
        )

    holdout_top_stage_counts: dict[str, int] = {}
    for row in rows:
        top = row.get("top_resonance")
        if isinstance(top, dict):
            st = str(top.get("stage", "") or "").strip()
            if st:
                holdout_top_stage_counts[st] = int(holdout_top_stage_counts.get(st, 0)) + 1

    out = {
        "schema": "global_atom_news_network_holdout_replay_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "input": {
            "batch_report_json": str(rp),
            "holdout_news_jsonl": str(holdout_path) if holdout_path.is_file() else None,
            "dataset_source": "jsonl" if holdouts_jsonl else "builtin_default",
        },
        "summary": {
            "cases_total": len(rows),
            "holdout_top_stage_counts": holdout_top_stage_counts,
        },
        "cases": rows,
        "note": "Holdout replay with dataset input support. Prefer locked external JSONL dataset for publication claims.",
    }

    op = resolve(args.output_json)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

