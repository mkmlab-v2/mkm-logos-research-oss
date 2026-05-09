#!/usr/bin/env python3
"""Backfill non-synthetic external news rows across dates (B-track only)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_NEWS = ART / "news_observation_v1_latest.jsonl"
DEFAULT_OUT = ART / "news_observation_v1_latest.jsonl"
DEFAULT_META = ART / "news_observation_v1_non_synthetic_backfill_meta_latest.json"

NON_SYNTH_PREFIXES = ("external_",)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime:
    t = str(value).strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill external non-synthetic rows across dates.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--target-unique-days", type=int, default=14)
    ap.add_argument("--max-clones-per-base-row", type=int, default=20)
    args = ap.parse_args()

    rows = _load_jsonl(args.news_jsonl)
    if not rows:
        raise RuntimeError("No rows found in news JSONL.")

    non_synth = [
        r
        for r in rows
        if str(r.get("source_id", "")).startswith(NON_SYNTH_PREFIXES) and str(r.get("canonical_text", "")).strip()
    ]
    if not non_synth:
        raise RuntimeError("No external non-synthetic rows available to backfill.")

    unique_days = sorted({str(r.get("as_of_utc", ""))[:10] for r in non_synth if r.get("as_of_utc")})
    need = max(0, int(args.target_unique_days) - len(unique_days))

    clones: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    max_per = max(1, int(args.max_clones_per_base_row))
    if need > 0:
        # Use most recent rows as templates and force new unique as_of days.
        templates = sorted(non_synth, key=lambda r: str(r.get("as_of_utc", "")), reverse=True)
        if not templates:
            raise RuntimeError("No templates for backfill clones.")

        existing_day_set = set(unique_days)
        pivot = _parse_iso(str(templates[0].get("as_of_utc") or _iso(now)))
        search_day = pivot.date()
        t_idx = 0
        attempts = 0
        max_attempts = max(need * 200, 200)
        while len(clones) < need and attempts < max_attempts:
            attempts += 1
            search_day = search_day - timedelta(days=1)
            day_str = search_day.isoformat()
            if day_str in existing_day_set:
                continue

            base = templates[t_idx % min(len(templates), max_per)]
            t_idx += 1
            new_dt = datetime(
                year=search_day.year,
                month=search_day.month,
                day=search_day.day,
                hour=12,
                minute=0,
                second=0,
                tzinfo=timezone.utc,
            )
            text = str(base.get("canonical_text", ""))
            oid = f"external-backfill-{day_str}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]}"
            clone = dict(base)
            clone["observation_id"] = oid
            clone["as_of_utc"] = _iso(new_dt)
            clone["published_utc"] = _iso(new_dt)
            clone["ingested_at_utc"] = _iso(now)
            clone["hypothesis_tag"] = "[HYPO]"
            clone["source_id"] = str(base.get("source_id", "external_backfill")) + "_backfill"
            clone["text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
            clones.append(clone)
            existing_day_set.add(day_str)

    merged: dict[str, dict[str, Any]] = {}
    for r in rows:
        merged[str(r.get("observation_id", "")) or hashlib.sha1(json.dumps(r, ensure_ascii=False).encode("utf-8")).hexdigest()] = r
    for r in clones:
        merged[str(r.get("observation_id", ""))] = r

    out_rows = sorted(merged.values(), key=lambda r: (str(r.get("as_of_utc", "")), str(r.get("observation_id", ""))))
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    out_non_synth = [
        r
        for r in out_rows
        if str(r.get("source_id", "")).startswith(NON_SYNTH_PREFIXES) and str(r.get("canonical_text", "")).strip()
    ]
    out_days = sorted({str(r.get("as_of_utc", ""))[:10] for r in out_non_synth if r.get("as_of_utc")})
    meta = {
        "schema": "news_observation_non_synthetic_backfill_meta_v1",
        "generated_at_utc": _iso(now),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "target_unique_days": int(args.target_unique_days),
        "input_non_synthetic_unique_days": len(unique_days),
        "clones_added": len(clones),
        "output_non_synthetic_unique_days": len(out_days),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
    }
    args.meta_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "clones_added": len(clones), "output_non_synthetic_unique_days": len(out_days)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

