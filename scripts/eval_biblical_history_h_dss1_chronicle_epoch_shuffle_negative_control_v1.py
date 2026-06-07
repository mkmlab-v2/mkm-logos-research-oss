#!/usr/bin/env python3
"""H-DSS1 chronicle epoch shuffle negative control (B-track falsification)."""

from __future__ import annotations

import argparse
import copy
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONICLE = ROOT / "docs/final/artifacts/chronicle_history_news_signal_history_latest.jsonl"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/chronicle_history_news_signal_h_dss1_daily_overlay_latest.jsonl"
DEFAULT_RESEARCH_MIX = ROOT / "docs/final/artifacts/chronicle_history_news_signal_research_decision_mix_latest.jsonl"
DEFAULT_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_HYP = ROOT / "docs/final/artifacts/biblical_resonance_hypotheses_v1.json"
DEFAULT_OUT = ROOT / "reports/biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _two_sided_p(ge_count: int, le_count: int, repeats: int) -> float:
    p_ge = ge_count / repeats
    p_le = le_count / repeats
    return round(min(1.0, 2.0 * min(p_ge, p_le)), 6)


def _parse_iso(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def _in_window(rows: list[dict[str, Any]], since: datetime) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        ts = _parse_iso(row.get("generated_at_utc")) or _parse_iso(row.get("as_of_utc"))
        if ts is not None and ts >= since:
            out.append(row)
    return out


def _group_match(text: str, group: list[str]) -> bool:
    return any(tok.lower() in text for tok in group)


def _hypothesis_match(text: str, groups: list[list[str]]) -> bool:
    return any(_group_match(text, g) for g in groups)


def _dss1_news_days(news_rows: list[dict[str, Any]], groups: list[list[str]]) -> set[str]:
    days: set[str] = set()
    for row in news_rows:
        txt = str(row.get("canonical_text", "")).lower()
        if not _hypothesis_match(txt, groups):
            continue
        ts = _parse_iso(row.get("as_of_utc")) or _parse_iso(row.get("published_utc"))
        if ts is not None:
            days.add(ts.date().isoformat())
    return days


def _overlap_hold_rate(chronicle_rows: list[dict[str, Any]], news_days: set[str]) -> tuple[float, int, int]:
    aligned = 0
    compared = 0
    for row in chronicle_rows:
        ts = _parse_iso(row.get("generated_at_utc")) or _parse_iso(row.get("as_of_utc"))
        if ts is None:
            continue
        day = ts.date().isoformat()
        if day not in news_days:
            continue
        compared += 1
        if str(row.get("final_decision", "")).upper() == "HOLD":
            aligned += 1
    rate = (aligned / compared) if compared else 0.0
    return rate, compared, aligned


DEFAULT_STRESS_TERMS: tuple[str, ...] = (
    "risk-off",
    "stress",
    "shock",
    "volatility",
    "liquidity thin",
    "credit spreads",
    "dead sea",
    "qumran",
    "apocrypha",
)


def _stress_terms(hyp_doc: dict[str, Any], hyp_cfg: dict[str, Any]) -> tuple[str, ...]:
    per_hyp = hyp_cfg.get("stress_terms_any")
    if isinstance(per_hyp, list) and per_hyp:
        return tuple(str(t).lower() for t in per_hyp)
    global_terms = hyp_doc.get("stress_terms_any")
    if isinstance(global_terms, list) and global_terms:
        return tuple(str(t).lower() for t in global_terms)
    return DEFAULT_STRESS_TERMS


def _composite_score(
    news_rows: list[dict[str, Any]],
    chronicle_rows: list[dict[str, Any]],
    hyp_cfg: dict[str, Any],
    hyp_doc: dict[str, Any],
    *,
    news_days: set[str] | None = None,
) -> dict[str, float]:
    groups = hyp_cfg.get("keyword_groups_any", [])
    if not isinstance(groups, list):
        groups = []
    matched = 0
    stress_hits = 0
    stress_terms = _stress_terms(hyp_doc, hyp_cfg)
    for row in news_rows:
        txt = str(row.get("canonical_text", "")).lower()
        if _hypothesis_match(txt, groups):
            matched += 1
            if any(t in txt for t in stress_terms):
                stress_hits += 1
    total_news = max(1, len(news_rows))
    coverage = matched / total_news
    stress_alignment = (stress_hits / matched) if matched > 0 else 0.0
    if news_days:
        hold_alignment, overlap_compared, _ = _overlap_hold_rate(chronicle_rows, news_days)
    else:
        overlap_compared = 0
        hold_rows = sum(1 for r in chronicle_rows if str(r.get("final_decision", "")).upper() == "HOLD")
        hold_alignment = (hold_rows / max(1, len(chronicle_rows))) if chronicle_rows else 0.0
    composite = (0.25 * coverage) + (0.25 * stress_alignment) + (0.5 * hold_alignment)
    return {
        "matched_rows": float(matched),
        "coverage_ratio": round(coverage, 6),
        "stress_alignment_ratio": round(stress_alignment, 6),
        "hold_alignment_ratio": round(hold_alignment, 6),
        "overlap_days_compared": float(overlap_compared),
        "composite_score": round(composite, 6),
    }


def _shuffle_final_decisions(rows: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    finals = [str(r.get("final_decision", "HOLD")) for r in rows]
    candidates = [str(r.get("candidate_decision", "HOLD")) for r in rows]
    if len(finals) < 2:
        return rows
    rng.shuffle(finals)
    rng.shuffle(candidates)
    out: list[dict[str, Any]] = []
    for row, fin, cand in zip(rows, finals, candidates):
        copy_row = copy.deepcopy(row)
        copy_row["final_decision"] = fin
        copy_row["candidate_decision"] = cand
        out.append(copy_row)
    return out


def _all_keyword_groups(hyp_doc: dict[str, Any], exclude_id: str) -> list[list[str]]:
    pool: list[list[str]] = []
    for h in hyp_doc.get("hypotheses") or []:
        if not isinstance(h, dict) or h.get("id") == exclude_id:
            continue
        groups = h.get("keyword_groups_any")
        if isinstance(groups, list):
            for g in groups:
                if isinstance(g, list) and g:
                    pool.append([str(x).lower() for x in g])
    return pool


def _shuffle_news_keyword_groups(
    news_rows: list[dict[str, Any]],
    rng: random.Random,
    hyp_doc: dict[str, Any],
    dss1_cfg: dict[str, Any],
) -> list[list[str]]:
    """Null keyword groups: sample same count of groups from other hypotheses."""
    observed_groups = dss1_cfg.get("keyword_groups_any", [])
    if not isinstance(observed_groups, list):
        observed_groups = []
    n_groups = max(1, len(observed_groups))
    pool = _all_keyword_groups(hyp_doc, str(dss1_cfg.get("id", "H-DSS1")))
    if not pool:
        return observed_groups if isinstance(observed_groups, list) else []
    return [rng.choice(pool) for _ in range(n_groups)]


def _composite_with_groups(
    news_rows: list[dict[str, Any]],
    chronicle_rows: list[dict[str, Any]],
    groups: list[list[str]],
    hyp_doc: dict[str, Any],
    dss1_cfg: dict[str, Any],
    *,
    news_days: set[str] | None = None,
) -> dict[str, float]:
    cfg = dict(dss1_cfg)
    cfg["keyword_groups_any"] = groups
    return _composite_score(news_rows, chronicle_rows, cfg, hyp_doc, news_days=news_days)


def _shuffle_epoch_labels(rows: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    stamps: list[str] = []
    for row in rows:
        ts = _parse_iso(row.get("generated_at_utc")) or _parse_iso(row.get("as_of_utc"))
        if ts is not None:
            stamps.append(ts.strftime("%Y-%m-%dT%H:%M:%SZ"))
    if len(stamps) < 2:
        return rows
    shuffled = stamps.copy()
    rng.shuffle(shuffled)
    out: list[dict[str, Any]] = []
    si = 0
    for row in rows:
        copy_row = copy.deepcopy(row)
        if (_parse_iso(copy_row.get("generated_at_utc")) or _parse_iso(copy_row.get("as_of_utc"))) is not None:
            new_stamp = shuffled[si]
            si += 1
            if copy_row.get("generated_at_utc"):
                copy_row["generated_at_utc"] = new_stamp
            if copy_row.get("as_of_utc"):
                copy_row["as_of_utc"] = new_stamp
        out.append(copy_row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="H-DSS1 chronicle epoch shuffle negative control.")
    ap.add_argument("--news-jsonl", type=Path, default=DEFAULT_NEWS)
    ap.add_argument("--chronicle-jsonl", type=Path, default=DEFAULT_CHRONICLE)
    ap.add_argument("--chronicle-overlay-jsonl", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--chronicle-research-mix-jsonl", type=Path, default=DEFAULT_RESEARCH_MIX)
    ap.add_argument("--hypotheses-json", type=Path, default=DEFAULT_HYP)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--shuffle-repeats", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.lookback_days)
    news_rows = _in_window(_load_jsonl(args.news_jsonl), since)
    mix_path = args.chronicle_research_mix_jsonl
    if mix_path.is_file():
        chronicle_rows = _in_window(_load_jsonl(mix_path), since)
        chronicle_source = str(mix_path)
    else:
        chronicle_rows = _in_window(_load_jsonl(args.chronicle_jsonl), since)
        overlay_rows = _in_window(_load_jsonl(args.chronicle_overlay_jsonl), since)
        if overlay_rows:
            chronicle_rows = chronicle_rows + overlay_rows
        chronicle_source = str(args.chronicle_jsonl)

    hyp_doc = _load_json(args.hypotheses_json)
    dss1 = next(
        (h for h in hyp_doc.get("hypotheses", []) if isinstance(h, dict) and h.get("id") == "H-DSS1"),
        None,
    )
    groups = dss1.get("keyword_groups_any", []) if isinstance(dss1, dict) else []
    if not isinstance(groups, list):
        groups = []

    news_days = _dss1_news_days(news_rows, groups)
    observed_rate, observed_compared, observed_aligned = _overlap_hold_rate(chronicle_rows, news_days)
    dss1_cfg = dss1 if isinstance(dss1, dict) else {}
    observed_composite = _composite_score(news_rows, chronicle_rows, dss1_cfg, hyp_doc, news_days=news_days)

    rng = random.Random(args.seed)
    null_rates: list[float] = []
    null_ge_observed = 0
    null_le_observed = 0
    null_composites: list[float] = []
    null_keyword_composites: list[float] = []
    decision_null_ge_observed = 0
    decision_null_le_observed = 0
    epoch_composite_null_ge_observed = 0
    epoch_composite_null_le_observed = 0
    keyword_null_ge_observed = 0
    keyword_null_le_observed = 0
    hold_decision_counts = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    for row in chronicle_rows:
        d = str(row.get("final_decision", "")).upper()
        if d in hold_decision_counts:
            hold_decision_counts[d] += 1
    repeats = max(1, args.shuffle_repeats)
    for _ in range(repeats):
        shuffled_epoch = _shuffle_epoch_labels(chronicle_rows, rng)
        rate, _, _ = _overlap_hold_rate(shuffled_epoch, news_days)
        null_rates.append(rate)
        if rate >= observed_rate:
            null_ge_observed += 1
        if rate <= observed_rate:
            null_le_observed += 1
        epoch_comp = _composite_score(
            news_rows, shuffled_epoch, dss1_cfg, hyp_doc, news_days=news_days
        )["composite_score"]
        if epoch_comp >= observed_composite["composite_score"]:
            epoch_composite_null_ge_observed += 1
        if epoch_comp <= observed_composite["composite_score"]:
            epoch_composite_null_le_observed += 1

        shuffled_decision = _shuffle_final_decisions(chronicle_rows, rng)
        comp = _composite_score(
            news_rows, shuffled_decision, dss1_cfg, hyp_doc, news_days=news_days
        )["composite_score"]
        null_composites.append(comp)
        if comp >= observed_composite["composite_score"]:
            decision_null_ge_observed += 1
        if comp <= observed_composite["composite_score"]:
            decision_null_le_observed += 1

        null_groups = _shuffle_news_keyword_groups(news_rows, rng, hyp_doc, dss1_cfg)
        null_news_days = _dss1_news_days(news_rows, null_groups)
        kw_comp = _composite_with_groups(
            news_rows, chronicle_rows, null_groups, hyp_doc, dss1_cfg, news_days=null_news_days
        )["composite_score"]
        null_keyword_composites.append(kw_comp)
        if kw_comp >= observed_composite["composite_score"]:
            keyword_null_ge_observed += 1
        if kw_comp <= observed_composite["composite_score"]:
            keyword_null_le_observed += 1

    payload = {
        "schema": "biblical_history_h_dss1_chronicle_epoch_shuffle_negative_control_v1",
        "hypothesis_id": "H-DSS1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "window_days": args.lookback_days,
        "inputs": {
            "news_jsonl": str(args.news_jsonl),
            "chronicle_jsonl": str(args.chronicle_jsonl),
            "chronicle_overlay_jsonl": str(args.chronicle_overlay_jsonl),
            "chronicle_research_mix_jsonl": str(mix_path),
            "chronicle_source_used": chronicle_source,
            "chronicle_final_decision_counts": hold_decision_counts,
            "shuffle_repeats": args.shuffle_repeats,
            "seed": args.seed,
            "h_dss1_news_match_day_count": len(news_days),
        },
        "observed": {
            "hold_alignment_on_h_dss1_news_days": round(observed_rate, 6),
            "overlap_days_compared": observed_compared,
            "hold_aligned_on_overlap_days": observed_aligned,
            "composite_score": observed_composite,
        },
        "null_distribution": {
            "hold_alignment_mean": round(sum(null_rates) / repeats, 6),
            "hold_alignment_median": round(sorted(null_rates)[repeats // 2], 6),
            "composite_score_decision_shuffle_mean": round(sum(null_composites) / repeats, 6),
            "composite_score_decision_shuffle_median": round(sorted(null_composites)[repeats // 2], 6),
            "composite_score_keyword_null_mean": round(sum(null_keyword_composites) / repeats, 6),
            "composite_score_keyword_null_median": round(sorted(null_keyword_composites)[repeats // 2], 6),
        },
        "permutation_p_values": {
            "hold_alignment_ge_observed": round(null_ge_observed / repeats, 6),
            "hold_alignment_two_sided": _two_sided_p(null_ge_observed, null_le_observed, repeats),
            "composite_score_ge_observed_decision_shuffle": round(decision_null_ge_observed / repeats, 6),
            "composite_score_le_observed_decision_shuffle": round(decision_null_le_observed / repeats, 6),
            "composite_score_two_sided_decision_shuffle": _two_sided_p(
                decision_null_ge_observed, decision_null_le_observed, repeats
            ),
            "composite_score_ge_observed_epoch_shuffle": round(epoch_composite_null_ge_observed / repeats, 6),
            "composite_score_two_sided_epoch_shuffle": _two_sided_p(
                epoch_composite_null_ge_observed, epoch_composite_null_le_observed, repeats
            ),
            "composite_score_ge_observed_keyword_null": round(keyword_null_ge_observed / repeats, 6),
            "composite_score_two_sided_keyword_null": _two_sided_p(
                keyword_null_ge_observed, keyword_null_le_observed, repeats
            ),
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": (
                "Uses research_decision_mix chronicle when available. "
                "Decision shuffle permutes final_decision; keyword null samples foreign hypothesis keyword groups. "
                "Low keyword_null or decision_shuffle p => observed composite less likely under null."
            ),
        },
        "fact_lock_notice": "Negative control only; not Track A or live trading gate.",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
