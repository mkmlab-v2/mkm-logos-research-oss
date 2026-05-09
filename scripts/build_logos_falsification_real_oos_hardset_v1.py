#!/usr/bin/env python3
"""Build harder real-OOS subset for theory discrimination."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_blind_split_latest.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_blind_split_hardset_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_real_oos_hardset_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _token_set(text: str) -> set[str]:
    return {t.strip(".,!?;:\"'()[]{}").lower() for t in text.split() if t.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Create harder real-OOS subset by filtering easy synthetic patterns.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--min-words", type=int, default=11)
    ap.add_argument("--max-source-share", type=float, default=0.5, help="Maximum share for dominant source_id in output.")
    args = ap.parse_args()

    rows = _load_jsonl(args.news_jsonl)
    if not rows:
        raise SystemExit(f"no rows: {args.news_jsonl}")

    # Step 1: prefer non-guided sources for higher difficulty.
    non_guided = [r for r in rows if str(r.get("source_id") or "") != "label_guided_seed"]
    guided = [r for r in rows if str(r.get("source_id") or "") == "label_guided_seed"]

    # Step 2: require minimum lexical richness and length.
    def hard_filter(r: dict[str, Any]) -> bool:
        text = str(r.get("canonical_text") or "")
        words = text.split()
        uniq = _token_set(text)
        return len(words) >= args.min_words and len(uniq) >= 8

    hard_non_guided = [r for r in non_guided if hard_filter(r)]
    hard_guided = [r for r in guided if hard_filter(r)]

    # Step 3: cap dominant source share to avoid one-template domination.
    out: list[dict[str, Any]] = []
    out.extend(hard_non_guided)
    if hard_guided:
        max_guided = int(len(out) * args.max_source_share)
        if max_guided < 10:
            max_guided = 10
        out.extend(hard_guided[:max_guided])

    # Keep deterministic order by as_of_utc then observation_id.
    out.sort(key=lambda r: (str(r.get("as_of_utc") or ""), str(r.get("observation_id") or "")))

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.output_jsonl.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + ("\n" if out else ""),
        encoding="utf-8",
    )

    src = Counter(str(r.get("source_id") or "") for r in out)
    summary = {
        "schema": "logos_falsification_real_oos_hardset_summary_v1",
        "generated_at_utc": _utc_now(),
        "input_rows": len(rows),
        "output_rows": len(out),
        "source_distribution": dict(src),
        "filters": {
            "exclude_primary_source": "label_guided_seed (preferred)",
            "min_words": args.min_words,
            "min_unique_tokens": 8,
            "max_source_share": args.max_source_share,
        },
        "output_jsonl": str(args.output_jsonl),
    }
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_rows": len(out), "output_jsonl": str(args.output_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
