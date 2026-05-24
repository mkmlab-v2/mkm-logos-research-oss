#!/usr/bin/env python3
"""Bootstrap hardset era gold overrides (operator_proxy_v1) from v2 heuristic gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_chronology_hardset_news_era_gold_v2_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json"


def _proxy_gold_for_event(event: dict[str, Any]) -> tuple[str, str]:
    tags = set(event.get("inferred_regime_tags_operator") or [])
    h1 = str(event.get("gold_era_id") or "")
    if h1 == "early_church_network" and not (tags & {"lehman", "risk"}):
        return (
            "modern_observational_field",
            "operator_proxy_v1: BTC/매크로 수치만·성경 키워드 없음 → 관측장(현대) 고정. heuristic early_church 거절.",
        )
    if tags & {"lehman", "risk"}:
        return (
            "judges_risk_cycle",
            "operator_proxy_v1: lehman/risk 태그 → judges_risk_cycle(위험 주기). rank_top1 modern과 분리.",
        )
    return (
        "modern_observational_field",
        "operator_proxy_v1: 리스크 태그 없음 → modern_observational_field.",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    if not gold_path.is_file():
        print(f"MISSING {gold_path}", file=sys.stderr)
        return 2

    gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))
    overrides: list[dict[str, Any]] = []
    for event in gold_doc.get("events") or []:
        oid = event.get("observation_id")
        if not oid:
            continue
        gid, rationale = _proxy_gold_for_event(event)
        overrides.append(
            {
                "observation_id": oid,
                "gold_era_id": gid,
                "acceptable_era_ids": [gid, "modern_observational_field", "judges_risk_cycle"],
                "rationale_ko": rationale,
            }
        )

    doc = {
        "schema": "logos_chronology_hardset_era_gold_overrides_v1",
        "version": "1.0.0",
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "human_signoff_required": True,
            "override_batch": "operator_proxy_v1",
            "human_signoff_completed": False,
        },
        "instructions_ko": (
            "operator_proxy_v1: inferred_regime_tags_operator 규칙으로 자동 생성. "
            "지휘관 검수·교체 전 MS/대외 인용 금지."
        ),
        "valid_era_ids_hint": [
            "modern_observational_field",
            "judges_risk_cycle",
            "exile_and_return",
            "intertestamental_empire_handoff",
            "gospel_logos_incarnate",
            "early_church_network",
        ],
        "overrides": overrides,
    }

    if args.dry_run:
        print(json.dumps({"n_overrides": len(overrides)}, ensure_ascii=False))
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} n={len(overrides)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
