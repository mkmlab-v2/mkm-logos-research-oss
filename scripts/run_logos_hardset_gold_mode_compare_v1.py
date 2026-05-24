#!/usr/bin/env python3
"""Compare hardset text_blind eval: v1 uniform modern vs v2 rank_top1 gold."""

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
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_hardset_gold_mode_compare_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval(gold: Path, out: Path) -> dict[str, Any]:
    cp = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--gold-json",
            str(gold),
            "--tag-mode",
            "text_blind",
            "--modern-boost",
            "0.08",
            "--boost-policy",
            "tier_v1",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode not in (0, 2):
        raise RuntimeError(cp.stderr or cp.stdout)
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    art = ROOT / "docs/final/artifacts"
    v1 = art / "logos_chronology_hardset_news_era_gold_v1_latest.json"
    v2 = art / "logos_chronology_hardset_news_era_gold_v2_latest.json"

    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_hardset_news_era_gold_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_hardset_news_era_gold_v2_v1.py")],
        cwd=str(ROOT),
        check=True,
    )

    d1 = _eval(v1, art / "_hardset_cmp_v1.json")
    d2 = _eval(v2, art / "_hardset_cmp_v2.json")

    s1 = d1.get("summary") or {}
    s2 = d2.get("summary") or {}

    report = {
        "schema": "logos_chronology_hardset_gold_mode_compare_v1",
        "generated_at_utc": _now(),
        "hypothesis_tier": "[HYPO]",
        "v1_uniform_modern": {"summary": s1, "gold_json": str(v1.name)},
        "v2_rank_top1": {"summary": s2, "gold_json": str(v2.name)},
        "delta_hit_at_1_strict": (
            None
            if s1.get("hit_at_1_strict") is None or s2.get("hit_at_1_strict") is None
            else round(float(s2["hit_at_1_strict"]) - float(s1["hit_at_1_strict"]), 6)
        ),
        "interpretation_ko": (
            "v1 92%는 단일 gold 편향 자기일치에 가깝다. v2는 gold 다양화 후 text_blind 실측; "
            "여전히 human row-level gold 아님."
        ),
    }

    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"v1 hit@1={s1.get('hit_at_1_strict')} v2 hit@1={s2.get('hit_at_1_strict')} delta={report['delta_hit_at_1_strict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
