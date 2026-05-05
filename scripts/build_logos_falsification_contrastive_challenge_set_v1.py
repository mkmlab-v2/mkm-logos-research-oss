#!/usr/bin/env python3
"""Build synthetic challenge set designed to force theory disagreements."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEWS = ROOT / "docs" / "final" / "artifacts" / "news_observation_v1_contrastive_challenge_latest.jsonl"
DEFAULT_LABELS = ROOT / "docs" / "final" / "artifacts" / "direction_label_bar_v1_contrastive_challenge_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "logos_falsification_contrastive_challenge_summary_latest.json"
PROFILE_ID = "logos_contrastive_challenge_v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(i: int, date_s: str, text: str) -> dict[str, Any]:
    return {
        "schema_version": "news_observation_v1",
        "observation_id": f"challenge-{i:04d}",
        "as_of_utc": f"{date_s}T09:00:00Z",
        "published_utc": f"{date_s}T09:00:00Z",
        "source_id": "contrastive_challenge",
        "canonical_text": text,
        "text_sha256": f"challenge_sha_{i:04d}",
        "ingested_at_utc": f"{date_s}T09:05:00Z",
        "dataset_partition": "locked_eval",
        "hypothesis_tag": "[HYPO]",
    }


def _label(date_s: str, direction: str, idx: int) -> dict[str, Any]:
    return {
        "schema_version": "direction_label_bar_v1",
        "instrument_id": "KOSPI",
        "label_date": date_s,
        "horizon": "1d",
        "direction": direction,
        "label_sha256": f"challenge_label_sha_{idx:04d}",
        "neutral_bps": 8.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build contrastive challenge news/label JSONL set.")
    ap.add_argument("--news-output", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--labels-output", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    # Pattern design: explicitly amplify known theory disagreements.
    # Group A (12 rows): Joseph-only keywords. Logos=down vs Counterfactual=up.
    # Group B (12 rows): Jubilee keywords without "slower tightening". I-Ching tends neutral.
    # Group C (12 rows): Mixed collision rows to raise contrastive density.
    # Group D (12 rows): Quantum-separation rows (risk-off heavy, label up) to
    #                    separate Logos(usually neutral) from Quantum(down).
    challenge_texts: list[tuple[str, str]] = []
    label_dirs: list[str] = []
    base_date = datetime.strptime("2024-03-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    day_offset = 0

    group_a_texts = [
        "liquidity thin consumption soft housing starts cool",
        "consumption soft liquidity thin housing starts cool",
        "housing starts cool liquidity thin consumption soft",
    ]
    for i in range(12):
        d = (base_date + timedelta(days=day_offset)).date().isoformat()
        t = group_a_texts[i % len(group_a_texts)]
        challenge_texts.append((d, t))
        label_dirs.append("down")  # favor Logos over counterfactual
        day_offset += 1

    group_b_texts = [
        "inventory build prices dip",
        "prices dip inventory build",
        "inventory build prices dip orders improve",
    ]
    for i in range(12):
        d = (base_date + timedelta(days=day_offset)).date().isoformat()
        t = group_b_texts[i % len(group_b_texts)]
        challenge_texts.append((d, t))
        label_dirs.append("up")
        day_offset += 1

    group_c_texts = [
        "breakthrough recovery risk-off credit spreads widen",
        "orders improve geopolitical volatility rises",
        "slower tightening inventory build risk-off",
        "recovery liquidity thin consumption soft",
        "prices dip risk-off housing starts cool",
        "export orders accelerate liquidity thin",
    ]
    group_c_labels = ["down", "down", "down", "down", "down", "up"]
    for i in range(12):
        d = (base_date + timedelta(days=day_offset)).date().isoformat()
        idx = i % len(group_c_texts)
        challenge_texts.append((d, group_c_texts[idx]))
        label_dirs.append(group_c_labels[idx])
        day_offset += 1

    group_d_texts = [
        "risk-off geopolitical credit spreads widen orders improve",
        "volatility rises risk-off export orders accelerate",
        "credit spreads widen geopolitical recovery orders improve",
        "risk-off volatility rises breakthrough orders improve",
    ]
    for i in range(12):
        d = (base_date + timedelta(days=day_offset)).date().isoformat()
        t = group_d_texts[i % len(group_d_texts)]
        challenge_texts.append((d, t))
        label_dirs.append("up")
        day_offset += 1

    news_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for i, (d, txt) in enumerate(challenge_texts, start=1):
        news_rows.append(_row(i, d, txt))
        # label_date must be strictly future for PIT join
        label_dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        label_date = label_dt.date().isoformat()
        label_rows.append(_label(label_date, label_dirs[i - 1], i))

    args.news_output.parent.mkdir(parents=True, exist_ok=True)
    args.news_output.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in news_rows) + "\n", encoding="utf-8")
    args.labels_output.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in label_rows) + "\n", encoding="utf-8")

    summary = {
        "schema": "logos_falsification_contrastive_challenge_summary_v1",
        "generated_at_utc": _utc_now(),
        "profile_id": PROFILE_ID,
        "news_rows": len(news_rows),
        "label_rows": len(label_rows),
        "news_output": str(args.news_output),
        "labels_output": str(args.labels_output),
        "content_sha256": {
            "news_jsonl": _sha256(args.news_output),
            "labels_jsonl": _sha256(args.labels_output),
        },
        "purpose": "Force prediction disagreements across Logos/Counterfactual/IChing/Quantum maps.",
    }
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "news_rows": len(news_rows), "labels_rows": len(label_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
