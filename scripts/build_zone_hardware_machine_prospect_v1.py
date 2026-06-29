#!/usr/bin/env python3
"""Build zone_hardware_machine prospect shard catalog (B-track, no Track A merge)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SHARD = ROOT / "codebook/shards/zone_hardware_machine.json"
DEFAULT_INPUT = ROOT / "data/btrack_fixtures/zone_hardware_machine_log_samples_v1.jsonl"
DEFAULT_PROSPECT = ROOT / "codebook/templates/zone_hardware_machine_templates_prospect_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/zone_hardware_machine_prospect_v1_latest.json"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/zone_hardware_machine_prospect_v1_latest.json"

TEXT_KEYS = ("text", "raw_text", "snippet", "content", "body")
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _load_shard(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _keywords(shard: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("routing_keywords", "must_keep_hard_terms", "must_keep_soft_terms"):
        for item in shard.get(field) or []:
            if item:
                keys.add(str(item).lower())
    return keys


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in TEXT_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _score_text(text: str, keywords: set[str]) -> int:
    lower = text.lower()
    score = sum(1 for kw in keywords if kw in lower)
    if "error" in lower or "traceback" in lower:
        score += 1
    if "{" in text and "}" in text:
        score += 1
    return score


def _must_keep_terms(text: str, keywords: set[str]) -> list[str]:
    found = sorted({tok for tok in TOKEN_RE.findall(text) if tok.lower() in keywords})
    return found[:8]


def _snippet_sha256(snippet: str) -> str:
    return hashlib.sha256(snippet.encode("utf-8")).hexdigest()


def build_prospect(
    *,
    input_jsonl: Path,
    shard_path: Path,
    min_score: int,
    max_rows: int,
) -> dict[str, Any]:
    shard = _load_shard(shard_path)
    keywords = _keywords(shard)
    prospect_rows: list[dict[str, Any]] = []
    scanned = 0

    for line in input_jsonl.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            continue
        text = _row_text(obj)
        if not text:
            continue
        scanned += 1
        score = _score_text(text, keywords)
        if score < min_score:
            continue
        row_id = str(obj.get("id") or f"hw-prospect-{len(prospect_rows):03d}")
        snippet = text[:500]
        prospect_rows.append(
            {
                "template_id": f"hwm_p{len(prospect_rows):03d}",
                "shard_id": str(shard.get("shard_id") or "zone_hardware_machine"),
                "language": "en",
                "snippet": snippet,
                "must_keep_terms": _must_keep_terms(snippet, keywords),
                "prospect": True,
                "source_row_id": row_id,
                "snippet_sha256": _snippet_sha256(snippet),
                "extract_score": score,
            }
        )
        if len(prospect_rows) >= max_rows:
            break

    return {
        "schema": "zone_hardware_machine_prospect_v1",
        "generated_at_utc": _utc(),
        "lane": "b_track_hypo",
        "disclaimer": "research_only",
        "send_gate": "HOLD",
        "track_a_active_untouched": True,
        "merge_policy": "prospect_only_no_auto_merge",
        "shard_path": _rel(shard_path),
        "input_jsonl": _rel(input_jsonl),
        "rows_scanned": scanned,
        "prospect_count": len(prospect_rows),
        "min_score": min_score,
        "prospect_rows": prospect_rows,
        "fallback_to_master_lexicon": "zone_hardware_machine L1 miss -> 41k master L2",
        "reproduce": [
            "py scripts/build_zone_hardware_machine_prospect_v1.py",
            "py scripts/build_zone_hardware_machine_prospect_v1.py --min-score 2 --max-rows 20",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--prospect-jsonl", type=Path, default=DEFAULT_PROSPECT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-json", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--min-score", type=int, default=2)
    ap.add_argument("--max-rows", type=int, default=20)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        print(f"error: missing input jsonl: {args.input_jsonl}", file=__import__("sys").stderr)
        return 2
    if not args.shard_json.is_file():
        print(f"error: missing shard json: {args.shard_json}", file=__import__("sys").stderr)
        return 2

    report = build_prospect(
        input_jsonl=args.input_jsonl.resolve(),
        shard_path=args.shard_json.resolve(),
        min_score=max(1, int(args.min_score)),
        max_rows=max(1, int(args.max_rows)),
    )

    prospect_rows = report.pop("prospect_rows")
    args.prospect_jsonl.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in prospect_rows).strip()
    args.prospect_jsonl.write_text((body + "\n") if body else "", encoding="utf-8")

    report["prospect_jsonl"] = _rel(args.prospect_jsonl)
    report["status"] = "ok" if prospect_rows else "empty"

    for out in (args.out_json, args.artifact_json):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False))
    return 0 if prospect_rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
