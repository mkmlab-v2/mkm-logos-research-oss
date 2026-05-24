#!/usr/bin/env python3
"""Draft Track A candidate bridge from SANDBOX evidence only (no prod score / no live).

Does NOT write docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "reports/sandbox_prophecy_panel_v1_latest.json"
DEFAULT_HOLDOUT = ROOT / "reports/sandbox_prophecy_holdout_report_v1_latest.json"
DEFAULT_PROMOTION = ROOT / "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json"
DEFAULT_ROLLUP = ROOT / "reports/sandbox_prophecy_rollup_v1_latest.json"
DEFAULT_MAINLINE_CANDIDATE = ROOT / "docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_track_a_candidate_bridge_draft_v1_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _panel_index(panel: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for t in panel.get("targets") or []:
        if isinstance(t, dict) and t.get("target_id"):
            out[str(t["target_id"])] = t
    return out


def _enrich(tid: str, panel_ix: dict[str, dict[str, Any]], *, tier: str, extra: dict[str, Any]) -> dict[str, Any]:
    p = panel_ix.get(tid) or {}
    row = {
        "target_id": tid,
        "tier": tier,
        "asset": p.get("asset"),
        "lens_profile": p.get("lens_profile"),
        "panel_hit_rate": p.get("hit_rate"),
        "n_evaluated": p.get("n_evaluated"),
        "alert_1_pass": p.get("alert_1_pass"),
    }
    row.update(extra)
    return row


def build_bridge_draft(
    *,
    panel: dict[str, Any],
    holdout: dict[str, Any] | None,
    promotion: dict[str, Any] | None,
    rollup: dict[str, Any] | None,
    mainline_candidate: dict[str, Any] | None,
    min_panel_hit: float = 0.55,
) -> dict[str, Any]:
    panel_ix = _panel_index(panel)
    holdout_pass = set((holdout or {}).get("holdout_pass_target_ids") or [])
    early_ids = {
        str(x.get("target_id"))
        for x in (rollup or {}).get("early_watchlist") or []
        if isinstance(x, dict) and x.get("target_id")
    }

    tier_holdout: list[dict[str, Any]] = []
    for tid in sorted(holdout_pass):
        if tid not in panel_ix:
            continue
        tier_holdout.append(
            _enrich(
                tid,
                panel_ix,
                tier="holdout_pass",
                extra={
                    "holdout_stable": True,
                    "bridge_readiness": "ready_for_human_review",
                    "note_ko": "홀드아웃 스냅샷 안정성 통과 — 휴먼 검토 후 별도 mainline 승격 절차.",
                },
            )
        )

    tier_early: list[dict[str, Any]] = []
    for tid in sorted(early_ids - holdout_pass):
        if tid not in panel_ix:
            continue
        try:
            if float(panel_ix[tid].get("hit_rate") or 0) < min_panel_hit:
                continue
        except (TypeError, ValueError):
            continue
        ew = next(
            (x for x in (rollup or {}).get("early_watchlist") or [] if x.get("target_id") == tid),
            {},
        )
        tier_early.append(
            _enrich(
                tid,
                panel_ix,
                tier="early_watchlist",
                extra={
                    "streak_days": ew.get("streak_days"),
                    "mean_hit_last_7d": ew.get("mean_hit_last_7d"),
                    "holdout_stable": False,
                    "bridge_readiness": "observe_until_3d_streak_or_holdout",
                    "note_ko": "2연속일 관측 — 본선 브리지 검토 전 홀드아웃·3일 streak 대기 권장.",
                },
            )
        )

    tier_staging: list[dict[str, Any]] = []
    seen = holdout_pass | early_ids
    for c in (promotion or {}).get("candidates") or []:
        if not isinstance(c, dict):
            continue
        tid = str(c.get("target_id") or "")
        if not tid or tid in seen:
            continue
        tier_staging.append(
            _enrich(
                tid,
                panel_ix,
                tier="panel_staging",
                extra={
                    "holdout_stable": c.get("holdout_stable"),
                    "bridge_readiness": "sandbox_panel_only",
                    "note_ko": "당일 패널 ≥ threshold — 홀드아웃·streak 미충족 시 연구 관측만.",
                },
            )
        )

    all_draft = tier_holdout + tier_early + tier_staging
    mainline_ref = None
    if mainline_candidate:
        mainline_ref = {
            "path": "docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json",
            "status": mainline_candidate.get("status"),
            "ensemble_profile": (mainline_candidate.get("btrack_stack") or {}).get("ensemble_profile"),
            "post_apply_30d_hit_rate": (mainline_candidate.get("btrack_stack") or {}).get(
                "post_apply_30d_hit_rate"
            ),
            "note_ko": "본선 후보 JSON은 SANDBOX 초안이 덮어쓰지 않음.",
        }

    if tier_holdout:
        next_action = "holdout_pass 타겟 human review → apply_prophecy_human_approval 별도 절차"
    elif tier_early:
        next_action = "early_watchlist 3일 streak 또는 holdout pass 대기 후 재생성"
    elif tier_staging:
        next_action = "스트림 달력일 축적 후 holdout/rollup 재평가"
    else:
        next_action = "sandbox 일일 체인 유지"

    return {
        "schema": "sandbox_prophecy_track_a_candidate_bridge_draft_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "status": "DRAFT_BRIDGE_ONLY",
        "promotion_mode": "sandbox_evidence_bridge_draft",
        "runtime_constraints": {
            "prod_score_mutation": False,
            "track_b_to_a_auto_bridge": False,
            "live_trading_enabled": False,
            "overwrites_prophecy_track_a_candidate_v1": False,
        },
        "policy": {
            "min_panel_hit": min_panel_hit,
            "tiers": ["holdout_pass", "early_watchlist", "panel_staging"],
        },
        "n_tier_holdout_pass": len(tier_holdout),
        "n_tier_early_watchlist": len(tier_early),
        "n_tier_panel_staging": len(tier_staging),
        "n_total_draft_rows": len(all_draft),
        "tier_holdout_pass": tier_holdout,
        "tier_early_watchlist": tier_early,
        "tier_panel_staging": tier_staging,
        "mainline_candidate_reference": mainline_ref,
        "recommended_next_human_action": next_action,
        "evidence_refs": {
            "panel": "reports/sandbox_prophecy_panel_v1_latest.json",
            "holdout": "reports/sandbox_prophecy_holdout_report_v1_latest.json",
            "promotion_research": "reports/sandbox_prophecy_promotion_research_pack_v1_latest.json",
            "rollup": "reports/sandbox_prophecy_rollup_v1_latest.json",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--promotion-json", type=Path, default=DEFAULT_PROMOTION)
    ap.add_argument("--rollup-json", type=Path, default=DEFAULT_ROLLUP)
    ap.add_argument("--mainline-candidate-json", type=Path, default=DEFAULT_MAINLINE_CANDIDATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-panel-hit", type=float, default=0.55)
    args = ap.parse_args()

    panel = _load(args.panel_json)
    if not panel:
        print(f"Missing panel: {args.panel_json}", file=__import__("sys").stderr)
        return 2

    doc = build_bridge_draft(
        panel=panel,
        holdout=_load(args.holdout_json),
        promotion=_load(args.promotion_json),
        rollup=_load(args.rollup_json),
        mainline_candidate=_load(args.mainline_candidate_json),
        min_panel_hit=args.min_panel_hit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(
        f"tiers: holdout={doc['n_tier_holdout_pass']} "
        f"early={doc['n_tier_early_watchlist']} staging={doc['n_tier_panel_staging']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
