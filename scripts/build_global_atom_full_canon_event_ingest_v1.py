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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return default
    if isinstance(value, dict):
        for k in ("value", "score", "corr", "correlation"):
            if k in value:
                return to_float(value.get(k), default)
    return default


def parse_verse_id(verse_id: str) -> tuple[str, int, int] | None:
    # Expected format: Book.Chapter.Verse (e.g., Gen.1.1)
    parts = verse_id.split(".")
    if len(parts) != 3:
        return None
    try:
        return parts[0], int(parts[1]), int(parts[2])
    except Exception:
        return None


def stage_books(stage: str) -> set[str]:
    if stage == "genesis":
        return {"Gen"}
    if stage == "torah":
        return {"Gen", "Exod", "Lev", "Num", "Deut"}
    if stage == "prophets":
        return {"Isa", "Jer", "Lam", "Ezek", "Dan", "Hos", "Joel", "Amos", "Obad", "Jonah", "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal"}
    if stage == "gospels":
        return {"Matt", "Mark", "Luke", "John"}
    return set()


def stage_regime(stage: str) -> str:
    return {
        "genesis": "creation_fall",
        "torah": "covenant_transition",
        "prophets": "empire_transition",
        "gospels": "kingdom_transition",
        "full_canon": "full_canon_transition",
    }[stage]


def row_features(row: dict[str, Any]) -> tuple[float, float, float, float, float, float, float]:
    p4 = row.get("pipeline4_unified_v2") if isinstance(row.get("pipeline4_unified_v2"), dict) else {}
    vec = p4.get("vector_4d") if isinstance(p4.get("vector_4d"), dict) else {}
    s = float(vec.get("S", 0.0) or 0.0)
    l = float(vec.get("L", 0.0) or 0.0)
    k = float(vec.get("K", 0.0) or 0.0)
    m = float(vec.get("M", 0.0) or 0.0)
    corr = to_float(row.get("correlation", 0.0), 0.0)
    p1d = to_float(row.get("p1_p4_distance_calibrated", 0.0), 0.0)
    p3d = to_float(row.get("p3_p4_distance", 0.0), 0.0)
    return s, l, k, m, corr, p1d, p3d


def score_event(rows: list[dict[str, Any]]) -> tuple[float, float, int]:
    if not rows:
        return 0.0, 0.0, 2
    sums = [0.0] * 7
    for r in rows:
        f = row_features(r)
        for i in range(7):
            sums[i] += f[i]
    n = float(len(rows))
    s, l, k, m, corr, p1d, p3d = [x / n for x in sums]
    vec_mean = (abs(s) + abs(l) + abs(k) + abs(m)) / 4.0
    hub = clamp((0.62 * vec_mean) + (0.23 * abs(corr)) + (0.15 * max(0.0, 1.0 - p1d)), 0.0, 1.0)
    path = clamp((0.58 * max(0.0, 1.0 - p3d)) + (0.27 * abs(k)) + (0.15 * abs(m)), 0.0, 1.0)
    cluster = int(round(clamp(4.0 + (10.0 * hub) + (8.0 * path) + (0.4 * len(rows)), 2.0, 48.0)))
    return round(hub, 6), round(path, 6), cluster


def build_events(rows: list[dict[str, Any]], window_size: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cur_key: tuple[str, int] | None = None
    cur_rows: list[dict[str, Any]] = []
    for row in rows:
        vid = str(row.get("verse_id", "") or "")
        parsed = parse_verse_id(vid)
        if parsed is None:
            continue
        book, chapter, verse = parsed
        key = (book, chapter)
        if cur_key != key or (cur_rows and len(cur_rows) >= window_size):
            if cur_rows:
                events.append({"key": cur_key, "rows": cur_rows})
            cur_key = key
            cur_rows = [row]
        else:
            cur_rows.append(row)
    if cur_rows:
        events.append({"key": cur_key, "rows": cur_rows})
    return events


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest event-level source into staged full-canon candidates.")
    ap.add_argument("--verse-source-json", default="data/logos/verse_4pipeline_full_31102.json")
    ap.add_argument("--stage", required=True, choices=["genesis", "torah", "prophets", "gospels", "full_canon"])
    ap.add_argument("--target-count", type=int, required=True)
    ap.add_argument("--window-size", type=int, default=5)
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    vp = resolve(args.verse_source_json)
    op = resolve(args.output_json)
    if not vp.is_file():
        raise SystemExit(f"missing verse source json: {vp}")
    rows = load_json(vp)
    if not isinstance(rows, list) or not rows:
        raise SystemExit("verse source is not a non-empty list")

    books = stage_books(args.stage)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id", "") or "")
        parsed = parse_verse_id(vid)
        if parsed is None:
            continue
        book, _, _ = parsed
        if books and book not in books:
            continue
        filtered.append(row)

    events = build_events(filtered, max(2, int(args.window_size)))
    if not events:
        raise SystemExit(f"no events selected for stage={args.stage}")

    picked: list[dict[str, Any]] = []
    for i, ev in enumerate(events):
        key = ev["key"]
        ev_rows = ev["rows"]
        if key is None:
            continue
        book, chapter = key
        first_vid = str(ev_rows[0].get("verse_id", ""))
        last_vid = str(ev_rows[-1].get("verse_id", ""))
        hub, path, cluster = score_event(ev_rows)
        picked.append(
            {
                "candidate_id": f"{args.stage}_ev_{len(picked)+1:05d}",
                "source_node_id": f"{book}.{chapter}::{first_vid}-{last_vid}",
                "hub_score": hub,
                "path_score": path,
                "cluster_size": cluster,
                "regime_tag": stage_regime(args.stage),
                "stage": args.stage,
                "book": book,
                "chapter": chapter,
                "event_span": {"start_verse_id": first_vid, "end_verse_id": last_vid, "verse_count": len(ev_rows)},
                "source_level": "event",
            }
        )
        if len(picked) >= int(args.target_count):
            break

    out = {
        "schema": "bible_meaning_insight_candidates_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "candidates": picked,
        "meta": {
            "profile": "global_atom_full_canon_event_ingest_v1",
            "stage": args.stage,
            "target_count": int(args.target_count),
            "selected_count": len(picked),
            "window_size": int(args.window_size),
            "verse_source_json": str(vp),
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

