#!/usr/bin/env python3
"""Operator human-margin report after commander hardset gold sign-off ([HYPO], not MS)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REP = ROOT / "reports"
DEFAULT_OUT_JSON = REP / "logos_hardset_era_human_margin_report_v1_latest.json"
DEFAULT_OUT_MD = REP / "logos_hardset_era_human_margin_report_v1_latest.md"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{100.0 * v:.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    readiness = _load(REP / "logos_hardset_era_gold_signoff_readiness_v1_latest.json")
    primary = _load(ART / "logos_chronology_hardset_text_blind_v2_eval_v1_latest.json")
    baseline = _load(ART / "logos_chronology_hardset_text_blind_v2_tier_v1_baseline_eval_v1_latest.json")
    hist_ms = _load(ART / "logos_chronology_era_blind_eval_text_blind_v1_latest.json")
    hist_v2 = _load(ART / "logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json")
    holdout = _load(REP / "logos_chronology_text_blind_v2_holdout_v1_latest.json")
    hist_ab = _load(REP / "logos_chronology_historical_tier_v2_ab_v1_latest.json")
    locked = _load(REP / "logos_chronology_locked_eval_policy_compare_v1_latest.json")
    merge = _load(REP / "logos_chronology_tier_v2_ssot_merge_v1_latest.json")
    overrides = _load(ART / "fixtures/logos_chronology_hardset_era_gold_overrides_v1.json")

    blockers: list[str] = []
    if not readiness or not readiness.get("ready_for_human_margin_report"):
        blockers.append("signoff_readiness_not_ready")
    if not primary:
        blockers.append("primary_ssot_eval_missing")
    elif (primary.get("inputs") or {}).get("boost_policy") != "tier_v2_locked_eval":
        blockers.append("primary_ssot_not_tier_v2_locked_eval")

    ps = primary.get("summary") or {} if primary else {}
    bs = baseline.get("summary") or {} if baseline else {}
    ms = hist_ms.get("summary") or {} if hist_ms else {}
    v2s = hist_v2.get("summary") or {} if hist_v2 else {}
    hold_cmp = (holdout or {}).get("compare") or {}
    lc = locked.get("compare") or {} if locked else {}
    ms_contract = (hist_ab or {}).get("ms_citation_contract") or {}

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = {
        "schema": "logos_hardset_era_human_margin_report_v1",
        "generated_at_utc": now,
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True, "ms_citation_allowed": False},
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "commander_signoff": {
            "human_signoff_completed": bool((overrides or {}).get("policy", {}).get("human_signoff_completed")),
            "n_overrides": len((overrides or {}).get("overrides") or []),
            "fixture": "docs/final/artifacts/fixtures/logos_chronology_hardset_era_gold_overrides_v1.json",
        },
        "ms_citation_contract": {
            "allowed_headline_metric": "historical_text_blind_hit_at_1_strict",
            "allowed_value": ms.get("hit_at_1_strict"),
            "baseline_contaminated_by_tier_v2": ms_contract.get("baseline_contaminated_by_tier_v2"),
        },
        "hardset_internal": {
            "ssot_primary": "docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json",
            "boost_policy": (primary.get("inputs") or {}).get("boost_policy") if primary else None,
            "hit_at_1_strict": ps.get("hit_at_1_strict"),
            "hit_at_1_relaxed": ps.get("hit_at_1_relaxed"),
            "locked_eval_hit_at_1_strict": ps.get("locked_eval_hit_at_1_strict"),
            "tier_v1_baseline_hit_at_1_strict": bs.get("hit_at_1_strict"),
            "delta_tier_v2_minus_tier_v1": lc.get("hit_at_1_delta_v2_minus_v1"),
            "rag_tier_v2_hit_at_1": lc.get("rag_tier_v2_hit_at_1"),
        },
        "text_blind_v2_research": {
            "not_ms_headline": True,
            "all_events_hit_at_1_strict": v2s.get("hit_at_1_strict"),
            "train_holdout_hit_at_1_strict": hold_cmp.get("train_holdout_hit_at_1_v2"),
            "train_holdout_delta_v2_minus_v1": hold_cmp.get("train_holdout_delta_v2_minus_v1"),
            "artifact": "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json",
            "holdout_report": "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json",
        },
        "interpretation_ko": (
            "대외·MS 인용은 historical text_blind만. hardset tier_v2·RAG·locked_eval uplift는 내부 engineering 증거. "
            "10x Moat·Track A·실매매 승격 주장 금지."
        ),
        "evidence_paths": [
            "reports/logos_chronology_era_blind_eval_digest_v1_latest.md",
            "reports/logos_chronology_tier_v2_ssot_merge_v1_latest.json",
            "reports/logos_chronology_locked_eval_policy_compare_v1_latest.json",
            "reports/logos_chronology_historical_tier_v2_ab_v1_latest.json",
            "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json",
        ],
        "merge_ok": (merge or {}).get("ok"),
    }

    lines = [
        "# Logos hardset era — human margin report",
        "",
        f"**Generated:** `{now}` · `[HYPO]` · `[NON_GATING]` · **not MS/public headline**",
        "",
        "## MS citation (대외 허용 1줄만)",
        "",
        f"- historical `text_blind` hit@1: **{_pct(ms.get('hit_at_1_strict'))}**",
        f"- tier_v2 baseline contamination: **`{ms_contract.get('baseline_contaminated_by_tier_v2')}`**",
        "",
        "## Hardset internal (commander-signed gold · tier_v2 SSOT)",
        "",
        f"- primary hit@1 strict: **{_pct(ps.get('hit_at_1_strict'))}** · relaxed **{_pct(ps.get('hit_at_1_relaxed'))}**",
        f"- locked_eval hit@1: **{_pct(ps.get('locked_eval_hit_at_1_strict'))}**",
        f"- tier_v1 baseline (compare only): **{_pct(bs.get('hit_at_1_strict'))}** · Δ v2−v1 **{lc.get('hit_at_1_delta_v2_minus_v1')}**",
        f"- rag_assisted tier_v2: **{_pct(lc.get('rag_tier_v2_hit_at_1'))}** (RAG 추가 uplift 없음 시 동일)",
        "",
        "## text_blind_v2 research (B-track · not MS/public)",
        "",
        f"- all-events hit@1: **{_pct(v2s.get('hit_at_1_strict'))}**",
        f"- train_holdout hit@1: **{_pct(hold_cmp.get('train_holdout_hit_at_1_v2'))}** · Δ vs v1 **{hold_cmp.get('train_holdout_delta_v2_minus_v1')}**",
        "- MS baseline remains historical text_blind v1 only until new eval contract sign-off.",
        "",
        "## Commander sign-off",
        "",
        f"- overrides: **{doc['commander_signoff']['n_overrides']}** · signed **`{doc['commander_signoff']['human_signoff_completed']}`**",
        "",
        "## Blockers",
        "",
        f"- `{blockers or ['none']}`",
        "",
        doc["interpretation_ko"],
        "",
    ]

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ready": doc["ready"], "blockers": blockers}, ensure_ascii=False))
    return 0 if doc["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
