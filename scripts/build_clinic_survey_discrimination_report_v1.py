"""
Offline discrimination / calibration report: physician_gold vs consumer_survey_only.

Joins ledger rows by ref_token. Does not claim clinical validity — research_only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.build_clinic_mvp_disagreement_summary_v1 import (  # noqa: E402
    _discover_jsonl,
    _load_records,
)
from scripts.clinic_constitution_mvp_ledger_v1 import WORKSPACE_DATA_REL  # noqa: E402

FOUR = frozenset({"taeeum", "soyang", "taeyang", "soeum"})


def _lane(r: dict[str, Any]) -> str:
    return str(r.get("label_lane") or "physician_gold")


def _ai_label(r: dict[str, Any]) -> str:
    return str((r.get("ai_hypothesis") or {}).get("constitution", "uncertain"))


def _physician_label(r: dict[str, Any]) -> str:
    return str((r.get("physician_constitution") or {}).get("label", "withheld"))


def build_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_ref: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for r in records:
        ref = str((r.get("encounter") or {}).get("ref_token", "")).strip()
        if not ref:
            continue
        lane = _lane(r)
        by_ref.setdefault(ref, {}).setdefault(lane, []).append(r)

    joins: list[dict[str, Any]] = []
    for ref, lanes in sorted(by_ref.items()):
        phys_rows = lanes.get("physician_gold", [])
        cons_rows = lanes.get("consumer_survey_only", [])
        if not phys_rows or not cons_rows:
            continue
        # latest per lane by ts_utc string sort
        phys = sorted(phys_rows, key=lambda x: str(x.get("ts_utc", "")))[-1]
        cons = sorted(cons_rows, key=lambda x: str(x.get("ts_utc", "")))[-1]
        pl = _physician_label(phys)
        ca = _ai_label(cons)
        pa = _ai_label(phys)
        joins.append(
            {
                "ref_token": ref,
                "physician_label": pl,
                "physician_ai_label": pa,
                "consumer_ai_label": ca,
                "physician_lane_comparable": pl in FOUR,
                "consumer_vs_physician_match": ca == pl if pl in FOUR else None,
                "physician_ai_vs_physician_match": pa == pl if pl in FOUR else None,
            }
        )

    n_join = len(joins)
    n_comp = sum(1 for j in joins if j["physician_lane_comparable"])
    n_cons_match = sum(1 for j in joins if j.get("consumer_vs_physician_match") is True)
    n_phys_ai_match = sum(1 for j in joins if j.get("physician_ai_vs_physician_match") is True)

    consumer_ai = Counter(_ai_label(r) for r in records if _lane(r) == "consumer_survey_only")
    physician_ai = Counter(_ai_label(r) for r in records if _lane(r) == "physician_gold")
    physician_gold = Counter(
        _physician_label(r)
        for r in records
        if _lane(r) == "physician_gold" and _physician_label(r) in FOUR
    )

    item_answer_rates: Counter[str] = Counter()
    for r in records:
        if _lane(r) != "consumer_survey_only":
            continue
        sr = r.get("survey_responses")
        if isinstance(sr, dict):
            for iid, val in sr.items():
                if int(val) >= 3:
                    item_answer_rates[str(iid)] += 1

    return {
        "schema": "clinic_survey_discrimination_report_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "research_only": True,
        "n_ledger_rows": len(records),
        "n_ref_token_joins": n_join,
        "calibration": {
            "n_physician_four_label": n_comp,
            "consumer_ai_vs_physician_match_rate": round(n_cons_match / n_comp, 4)
            if n_comp
            else None,
            "physician_lane_ai_vs_physician_match_rate": round(n_phys_ai_match / n_comp, 4)
            if n_comp
            else None,
            "operator_hint": (
                "n_physician_four_label이 작으면 교정 해석 금지. "
                "원장 확정 4진을 physician_gold에 먼저 쌓을 것."
            ),
        },
        "joins_sample": joins[:20],
        "distribution": {
            "consumer_survey_ai": dict(sorted(consumer_ai.items())),
            "physician_gold_ai": dict(sorted(physician_ai.items())),
            "physician_gold_confirmed": dict(sorted(physician_gold.items())),
        },
        "item_high_score_counts_ge3": dict(sorted(item_answer_rates.items())),
        "weight_tuning_next": [
            "physician_gold에 확정 4진 누적",
            "joins에서 consumer_ai_vs_physician 불일치 ref_token → 문항 가중 조정",
            "clinic_constitution_survey_item_bank_v1.json constitution_hints 갱신",
            "재실행: build_clinic_survey_discrimination_report_v1.py",
        ],
        "guards": {
            "not_for_track_a_promotion": True,
            "not_clinical_diagnosis": True,
            "do_not_use_consumer_match_as_marketing_accuracy": True,
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Clinic survey discrimination report v1")
    p.add_argument("--out", type=Path, default=Path("reports/clinic_survey_discrimination_report_latest.json"))
    args = p.parse_args(argv)
    root = _ROOT
    clinic_dir = root / WORKSPACE_DATA_REL
    paths = _discover_jsonl(clinic_dir)
    records, errors = _load_records(paths)
    report = build_report(records)
    if errors:
        report["parse_errors_sample"] = errors[:10]
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: joins={report['n_ref_token_joins']} "
        f"physician_4label={report['calibration']['n_physician_four_label']} -> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
