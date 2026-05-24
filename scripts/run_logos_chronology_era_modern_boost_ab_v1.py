#!/usr/bin/env python3
"""AB: modern_observational_field score boost (0.08 vs 0) on historical gold + narrative tier."""

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
DEFAULT_GOLD = ROOT / "docs/final/artifacts/fixtures/logos_chronology_historical_era_gold_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_era_modern_boost_ab_v1_latest.json"
DEFAULT_REVAL = ROOT / "docs/final/artifacts/logos_symbolic_revalidation_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_eval(gold: Path, boost: float, out: Path) -> dict[str, Any]:
    cp = subprocess.run(
        [
            sys.executable,
            str(EVAL),
            "--gold-json",
            str(gold),
            "--tag-mode",
            "gold_tags",
            "--modern-boost",
            str(boost),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return json.loads(out.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--boost-a", type=float, default=0.08)
    ap.add_argument("--boost-b", type=float, default=0.0)
    ap.add_argument("--append-revalidation", type=Path, default=DEFAULT_REVAL)
    args = ap.parse_args()

    gold = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    tmp_a = out.parent / "_ab_boost_a.json"
    tmp_b = out.parent / "_ab_boost_b.json"
    doc_a = _run_eval(gold, args.boost_a, tmp_a)
    doc_b = _run_eval(gold, args.boost_b, tmp_b)

    def _tier_rate(doc: dict[str, Any], tier: str) -> float | None:
        rows = [r for r in doc.get("rows") or [] if r.get("tier") == tier]
        if not rows:
            return None
        return sum(1 for r in rows if r.get("hit_at_1_strict")) / len(rows)

    narrative_a = _tier_rate(doc_a, "biblical_narrative")
    narrative_b = _tier_rate(doc_b, "biblical_narrative")

    report = {
        "schema": "logos_chronology_era_modern_boost_ab_v1",
        "generated_at_utc": _now(),
        "hypothesis_tier": "[HYPO]",
        "policy": doc_a.get("policy"),
        "inputs": {"gold_json": str(gold.relative_to(ROOT)).replace("\\", "/")},
        "variants": {
            "boost_on": {
                "modern_boost": args.boost_a,
                "summary": doc_a.get("summary"),
                "narrative_hit_at_1_strict": narrative_a,
            },
            "boost_off": {
                "modern_boost": args.boost_b,
                "summary": doc_b.get("summary"),
                "narrative_hit_at_1_strict": narrative_b,
            },
        },
        "delta_narrative_hit_at_1": (
            None
            if narrative_a is None or narrative_b is None
            else round(narrative_b - narrative_a, 6)
        ),
        "recommendation": (
            "narrative_tier: prefer boost_off for discrimination; "
            "macro_landmark: keep small boost optional."
            if narrative_b is not None and narrative_a is not None and narrative_b > narrative_a
            else "insufficient_delta"
        ),
        "note": "AB on era alignment only; not price prophecy or Track A.",
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rev = args.append_revalidation
    if rev and (rev if rev.is_absolute() else ROOT / rev).is_file():
        rev_path = rev if rev.is_absolute() else ROOT / rev
        reval_doc = json.loads(rev_path.read_text(encoding="utf-8"))
        reval_doc["non_synthetic_era_modern_boost_ab_v1"] = report
        reval_doc["non_synthetic_era_blind_appended_at_utc"] = _now()
        rev_path.write_text(json.dumps(reval_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {out}")
    print(
        f"narrative hit@1 boost_on={narrative_a} boost_off={narrative_b} "
        f"delta={report['delta_narrative_hit_at_1']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
