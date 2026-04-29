#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
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


def tokenize(text: str) -> set[str]:
    cleaned = text.replace(",", " ").replace(".", " ").replace("/", " ").replace("-", " ")
    return {t.strip().lower() for t in cleaned.split() if t.strip()}


def score_stage(tokens: set[str], stage: str) -> float:
    lex = {
        "genesis": {"origin", "creation", "reset", "birth"},
        "torah": {"law", "policy", "regulation", "discipline", "covenant"},
        "prophets": {"collapse", "war", "crisis", "judgment", "empire", "conflict"},
        "gospels": {"recovery", "relief", "support", "mercy", "stabilization"},
        "full_canon": {"global", "systemic", "transition", "regime", "reallocation"},
    }
    inter = len(tokens.intersection(lex.get(stage, set())))
    return inter / max(1, len(lex.get(stage, set())))


def top_stages(tokens: set[str], stages: list[dict[str, Any]], k: int = 2) -> list[dict[str, Any]]:
    rows = []
    for s in stages:
        if not isinstance(s, dict):
            continue
        stage = str(s.get("stage") or "")
        edges = float(s.get("edge_count") or 0.0)
        density = edges ** 0.5
        resonance = score_stage(tokens, stage) * density
        rows.append(
            {
                "stage": stage,
                "resonance_score": round(resonance, 6),
                "edge_count": s.get("edge_count"),
                "node_count": s.get("node_count"),
                "phase_transition_signal": s.get("phase_transition_signal"),
            }
        )
    rows.sort(key=lambda x: x["resonance_score"], reverse=True)
    return rows[:k]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run daily Pre-News shadow projection against global atom network.")
    ap.add_argument("--batch-report-json", default="docs/final/artifacts/global_atom_full_canon_batch_report_latest.json")
    ap.add_argument("--pre-news-input-json", default="docs/final/artifacts/pre_news_shadow_input_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/pre_news_shadow_projection_latest.json")
    ap.add_argument("--log-jsonl", default="reports/pre_news_shadow_projection_log.jsonl")
    args = ap.parse_args()

    report_path = resolve(args.batch_report_json)
    input_path = resolve(args.pre_news_input_json)
    out_path = resolve(args.output_json)
    log_path = resolve(args.log_jsonl)
    for p in (report_path, input_path):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    report = load(report_path)
    stages = report.get("stages") if isinstance(report.get("stages"), list) else []
    inp = load(input_path)
    rows = inp.get("rows") if isinstance(inp.get("rows"), list) else []
    if not rows:
        raise SystemExit("pre-news input rows is empty")

    projections = []
    for i, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        headline = str(row.get("headline", "") or "").strip()
        if not headline:
            continue
        toks = tokenize(headline)
        top2 = top_stages(toks, stages, k=2)
        top = top2[0] if top2 else {}
        projections.append(
            {
                "row_id": row.get("row_id", f"row_{i:03d}"),
                "headline": headline,
                "source": row.get("source"),
                "timestamp_utc": row.get("timestamp_utc"),
                "top_resonance": top,
                "top2_resonance": top2,
                "insight": f"Pre-News shadow resonance points first to `{top.get('stage')}` under current network topology.",
            }
        )

    out = {
        "schema": "pre_news_shadow_projection_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "input": {"batch_report_json": str(report_path), "pre_news_input_json": str(input_path)},
        "summary": {"rows_total": len(projections), "source_mode": (report.get("summary") or {}).get("source_mode")},
        "projections": projections,
        "note": "Shadow-only observation. Not connected to live trading triggers.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    stage_counter: Counter[str] = Counter()
    for p in projections:
        if not isinstance(p, dict):
            continue
        top = p.get("top_resonance")
        if isinstance(top, dict):
            stage = str(top.get("stage", "") or "").strip()
            if stage:
                stage_counter[stage] += 1
    dominant_stage = stage_counter.most_common(1)[0][0] if stage_counter else None

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "generated_at_utc": out["generated_at_utc"],
                    "output_json": str(out_path),
                    "rows": len(projections),
                    "primary_top_stage": dominant_stage,
                    "top_stage_counts": dict(stage_counter),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    print(str(out_path))
    print(str(log_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

