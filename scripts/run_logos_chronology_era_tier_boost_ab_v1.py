#!/usr/bin/env python3
"""AB: global vs tier_v1 modern boost on historical gold (gold_tags)."""

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
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_era_tier_boost_ab_v1_latest.json"
DEFAULT_REVAL = ROOT / "docs/final/artifacts/logos_symbolic_revalidation_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(
    gold: Path,
    boost: float,
    policy: str,
    out: Path,
) -> dict[str, Any]:
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
            "--boost-policy",
            policy,
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
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--macro-boost", type=float, default=0.08)
    ap.add_argument("--append-revalidation", type=Path, default=DEFAULT_REVAL, nargs="?")
    args = ap.parse_args()

    gold = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    tmp = out.parent

    variants = {
        "global_boost_off": _run(gold, 0.0, "global", tmp / "_tier_ab_global_off.json"),
        "global_boost_on": _run(gold, args.macro_boost, "global", tmp / "_tier_ab_global_on.json"),
        "tier_v1_macro_boost": _run(gold, args.macro_boost, "tier_v1", tmp / "_tier_ab_tier_v1.json"),
    }

    def _narr(doc: dict[str, Any]) -> float | None:
        return (doc.get("summary") or {}).get("narrative_hit_at_1_strict")

    n_off = _narr(variants["global_boost_off"])
    n_on = _narr(variants["global_boost_on"])
    n_tier = _narr(variants["tier_v1_macro_boost"])

    report = {
        "schema": "logos_chronology_era_tier_boost_ab_v1",
        "generated_at_utc": _now(),
        "hypothesis_tier": "[HYPO]",
        "policy": variants["tier_v1_macro_boost"].get("policy"),
        "inputs": {"gold_json": str(gold.relative_to(ROOT)).replace("\\", "/"), "macro_boost": args.macro_boost},
        "variants": {k: {"summary": v.get("summary"), "narrative_hit_at_1_strict": _narr(v)} for k, v in variants.items()},
        "delta_narrative_tier_v1_vs_global_on": (
            None if n_tier is None or n_on is None else round(n_tier - n_on, 6)
        ),
        "recommendation": (
            "Prefer boost_policy=tier_v1 with macro_boost=0.08: narrative unblocked, macro retains boost."
            if n_tier is not None and n_on is not None and n_tier >= n_on
            else "Review tier_v1 vs global_on on disk rows."
        ),
        "note": "Narrative tier only gets boost=0 under tier_v1; not price prophecy or Track A.",
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rev = args.append_revalidation
    if rev and (rev if rev.is_absolute() else ROOT / rev).is_file():
        rev_path = rev if rev.is_absolute() else ROOT / rev
        reval_doc = json.loads(rev_path.read_text(encoding="utf-8"))
        reval_doc["non_synthetic_era_tier_boost_ab_v1"] = report
        reval_doc["non_synthetic_era_blind_appended_at_utc"] = _now()
        rev_path.write_text(json.dumps(reval_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {out}")
    print(f"narrative: global_off={n_off} global_on={n_on} tier_v1={n_tier} delta_vs_on={report['delta_narrative_tier_v1_vs_global_on']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
