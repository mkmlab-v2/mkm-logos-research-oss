#!/usr/bin/env python3
"""KO vs EN headline text_blind_v2 probe (B-track OOV; MS v1 unchanged)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval_logos_chronology_era_blind_v1.py"
GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
EN = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_en_headlines_v1.json"
CHRONO = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
OUT_KO = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json"
OUT_EN = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_en_headline_v1_latest.json"
OUT_AB = ROOT / "reports/logos_chronology_text_blind_v2_en_headline_ab_v1_latest.json"

from summarize_logos_chronology_partition_holdout_v1 import (  # noqa: E402
    PARTITIONS,
    _load,
    _partition_slice,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_eval(text_source: str, out_json: Path, modern_boost: float, boost_policy: str) -> tuple[int, dict[str, Any]]:
    cmd = [
        sys.executable,
        str(EVAL),
        "--gold-json",
        str(GOLD),
        "--chronology-json",
        str(CHRONO),
        "--output-json",
        str(out_json),
        "--tag-mode",
        "text_blind_v2",
        "--text-source",
        text_source,
        "--en-headlines-json",
        str(EN),
        "--modern-boost",
        str(modern_boost),
        "--boost-policy",
        boost_policy,
    ]
    print("+", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd, cwd=str(ROOT))
    summary: dict[str, Any] = {}
    if out_json.is_file():
        summary = dict(_load(out_json).get("summary") or {})
    return rc, summary


def _compare(ko: dict[str, Any], en: dict[str, Any]) -> dict[str, Any]:
    by_partition: dict[str, Any] = {}
    for part in PARTITIONS:
        sk = _partition_slice(ko, part)
        se = _partition_slice(en, part)
        h_ko = float(sk.get("hit_at_1_strict") or 0.0)
        h_en = float(se.get("hit_at_1_strict") or 0.0)
        by_partition[part] = {
            "headline_ko_v2": sk,
            "headline_en_v2": se,
            "delta_en_minus_ko": round(h_en - h_ko, 6),
        }
    hold = by_partition["train_holdout"]
    return {
        "all_events_hit_at_1_ko": (ko.get("summary") or {}).get("hit_at_1_strict"),
        "all_events_hit_at_1_en": (en.get("summary") or {}).get("hit_at_1_strict"),
        "train_holdout_hit_at_1_ko": (hold.get("headline_ko_v2") or {}).get("hit_at_1_strict"),
        "train_holdout_hit_at_1_en": (hold.get("headline_en_v2") or {}).get("hit_at_1_strict"),
        "by_partition": by_partition,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modern-boost", type=float, default=0.08)
    ap.add_argument("--boost-policy", default="tier_v1")
    ap.add_argument("--skip-ko-rerun", action="store_true")
    args = ap.parse_args()

    rc_ko = 0
    if args.skip_ko_rerun and OUT_KO.is_file():
        ko_doc = _load(OUT_KO)
    else:
        rc_ko, _ = _run_eval("headline_ko", OUT_KO, args.modern_boost, args.boost_policy)
        ko_doc = _load(OUT_KO) if OUT_KO.is_file() else {}

    rc_en, _ = _run_eval("headline_en", OUT_EN, args.modern_boost, args.boost_policy)
    if rc_ko != 0 or rc_en != 0:
        return 1

    en_doc = _load(OUT_EN)
    compare = _compare(ko_doc, en_doc)
    ab = {
        "schema": "logos_chronology_text_blind_v2_en_headline_ab_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "ms_headline_unchanged": True,
            "ms_citation_still": "text_blind_tier_v1_only",
            "en_headlines_sidecar": str(EN.relative_to(ROOT)).replace("\\", "/"),
        },
        "compare": compare,
        "note_ko": (
            "EN probe uses research sidecar headline_en glosses, not live OOV news. "
            "MS baseline remains historical text_blind v1 (~6.4%)."
        ),
    }
    OUT_AB.parent.mkdir(parents=True, exist_ok=True)
    OUT_AB.write_text(json.dumps(ab, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(compare, ensure_ascii=False, default=str))
    print(f"WROTE: {OUT_AB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
