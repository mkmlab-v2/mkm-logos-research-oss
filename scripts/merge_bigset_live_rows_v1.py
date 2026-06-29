#!/usr/bin/env python3
"""Merge live BigSet dataset rows into Tier-0 CSV (dedupe by source_url, drop fixtures).

Reproducible:
  py scripts/merge_bigset_live_rows_v1.py
  py scripts/merge_bigset_live_rows_v1.py --dataset-id jd7awn474kqjrm2hezbej1at9989839j
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CSV = ROOT / "docs/research/raw/bigset_benei_haelohim_cross_refs_tier0_v1.csv"
DEFAULT_ART = ROOT / "docs/final/artifacts/bigset_live_rows_merge_v1_latest.json"
FIXTURE_HOSTS = ("example.org", "example.com")

TOPIC_CONFLICT_GROUPS: dict[str, set[str]] = {
    "benei_haelohim_cross_refs": {"MKM_CONCEPT_SONS_OF_GOD", "Sons_of_God_Theological_Interpretation"},
    "nephilim_watcher_cross_refs": {"MKM_CONCEPT_NEPHILIM"},
}


def _topic_slug_from_csv(csv_path: Path) -> str | None:
    name = csv_path.name
    if not name.startswith("bigset_") or not name.endswith("_tier0_v1.csv"):
        return None
    return name.removeprefix("bigset_").removesuffix("_tier0_v1.csv")


def _row_matches_topic(row: dict[str, Any], topic_slug: str | None) -> bool:
    if not topic_slug:
        return True
    allowed = TOPIC_CONFLICT_GROUPS.get(topic_slug)
    if not allowed:
        return True
    gid = str(row.get("conflict_group_id") or "").strip()
    if gid in allowed:
        return True
    if topic_slug == "nephilim_watcher_cross_refs":
        blob = " ".join(
            str(row.get(k) or "")
            for k in ("excerpt", "interpretation_ko", "verse_ref", "tradition")
        ).lower()
        return any(k in blob for k in ("nephilim", "watcher", "1 enoch", "jubilees"))
    return gid in allowed or not gid


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bigset_exe() -> str:
    return shutil.which("bigset") or shutil.which("bigset.cmd") or "bigset"


def _list_dataset_ids() -> list[str]:
    proc = subprocess.run(
        [_bigset_exe(), "list"],
        capture_output=True,
        text=True,
        shell=bool(sys.platform == "win32"),
    )
    ids: list[str] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if parts and parts[0].startswith("jd"):
            ids.append(parts[0])
    return ids


def _rows_for_dataset(dataset_id: str) -> list[dict[str, Any]]:
    proc = subprocess.run(
        [_bigset_exe(), "rows", dataset_id],
        capture_output=True,
        text=True,
        shell=bool(sys.platform == "win32"),
    )
    rows: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _is_fixture(url: str) -> bool:
    u = url.lower()
    return any(h in u for h in FIXTURE_HOSTS) or "[hypo] fixture" in u


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if not str(out.get("citation_lock_anchor") or "").strip():
        src = str(out.get("source_url") or "").strip()
        if src:
            out["citation_lock_anchor"] = src
    if not str(out.get("interpretation_ko") or "").strip():
        ex = str(out.get("excerpt") or "").strip()
        if ex:
            out["interpretation_ko"] = ex[:500]
    out.setdefault("hypothesis_tier", "B")
    out.setdefault("research_only", "true")
    out.setdefault("send_gate_row", "HOLD")
    out.setdefault("conflict_group_id", "MKM_CONCEPT_SONS_OF_GOD")
    return out


def merge_rows(
    *,
    dataset_ids: list[str] | None,
    csv_path: Path,
    include_csv: bool = True,
    topic_slug: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    slug = topic_slug or _topic_slug_from_csv(csv_path)
    ids = dataset_ids or _list_dataset_ids()
    by_url: dict[str, dict[str, Any]] = {}
    sources: dict[str, int] = {}
    filtered_out = 0

    for ds in ids:
        got = _rows_for_dataset(ds)
        if got:
            sources[ds] = len(got)
        for row in got:
            url = str(row.get("source_url") or "").strip()
            if not url or _is_fixture(url):
                continue
            norm = _normalize_row(row)
            if not _row_matches_topic(norm, slug):
                filtered_out += 1
                continue
            by_url[url] = norm

    if include_csv and csv_path.is_file():
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                url = str(row.get("source_url") or "").strip()
                if not url:
                    continue
                if _is_fixture(url):
                    by_url[url] = dict(row)
                    continue
                norm = _normalize_row(row)
                if not _row_matches_topic(norm, slug):
                    filtered_out += 1
                    continue
                by_url[url] = norm

    merged = list(by_url.values())
    meta = {
        "dataset_ids_scanned": ids,
        "rows_per_dataset": sources,
        "merged_rows": len(merged),
        "topic_slug": slug,
        "topic_filtered_out": filtered_out,
    }
    return merged, meta


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = sorted({k for r in rows for k in r})
    for col in ("source_url", "citation_lock_anchor", "hypothesis_tier", "research_only", "send_gate_row"):
        if col not in fieldnames:
            fieldnames.append(col)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    ap.add_argument("--dataset-id", action="append", dest="dataset_ids")
    ap.add_argument("--topic-slug", default=None, help="filter rows by topic conflict groups")
    args = ap.parse_args()
    csv_path = args.csv if args.csv.is_absolute() else (ROOT / args.csv)

    rows, meta = merge_rows(
        dataset_ids=args.dataset_ids,
        csv_path=csv_path,
        topic_slug=args.topic_slug,
    )
    write_csv(rows, csv_path)

    doc = {
        "schema": "bigset_live_rows_merge_v1",
        "generated_at_utc": _now(),
        "ok": len(rows) > 0,
        "research_only": True,
        "send_gate": "HOLD",
        "csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(rows),
        **meta,
        "reproduce": "py scripts/merge_bigset_live_rows_v1.py",
    }
    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "rows": len(rows), "csv": doc["csv"]}, ensure_ascii=False))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
