#!/usr/bin/env python3
"""One-page operator digest for era blind eval artifacts ([HYPO], NON_GATING)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REP = ROOT / "reports"
DEFAULT_OUT = ROOT / "reports/logos_chronology_era_blind_eval_digest_v1_latest.md"


def _load(name: str, base: Path | None = None) -> dict[str, Any] | None:
    p = (base or ART) / name
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{100.0 * v:.1f}%"


def main() -> int:
    hist_g = _load("logos_chronology_era_blind_eval_v1_latest.json")
    hist_t = _load("logos_chronology_era_blind_eval_text_blind_v1_latest.json")
    hard = _load("logos_chronology_hardset_text_blind_eval_v1_latest.json")
    hard2 = _load("logos_chronology_hardset_text_blind_v2_eval_v1_latest.json")
    hard2_rag = _load("logos_chronology_hardset_rag_assisted_v2_tier_v2_eval_v1_latest.json")
    hcmp = _load("logos_chronology_hardset_gold_mode_compare_v1_latest.json")
    ab = _load("logos_chronology_era_modern_boost_ab_v1_latest.json")
    tab = _load("logos_chronology_era_tier_boost_ab_v1_latest.json")
    tier_eval = _load("logos_chronology_era_blind_eval_tier_v1_latest.json")
    dmap = _load("logos_chronology_dynamic_map_v1_latest.json")
    hist_ab = _load("logos_chronology_historical_tier_v2_ab_v1_latest.json", REP)
    locked_cmp = _load("logos_chronology_locked_eval_policy_compare_v1_latest.json", REP)
    hist_rag_t2 = _load("logos_chronology_era_blind_eval_rag_assisted_tier_v2_v1_latest.json")
    hist_v2 = _load("logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json")
    v2_ab = _load("logos_chronology_text_blind_v2_ab_v1_latest.json", REP)
    v2_hold = _load("logos_chronology_text_blind_v2_holdout_v1_latest.json", REP)
    v2_hint_off = _load("logos_chronology_text_blind_v2_hint_off_ab_v1_latest.json", REP)
    v2_en = _load("logos_chronology_text_blind_v2_en_headline_ab_v1_latest.json", REP)
    margin = _load("logos_hardset_era_human_margin_report_v1_latest.json", REP)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Logos chronology era blind eval — operator digest",
        "",
        f"**Generated:** `{now}` · `[HYPO]` · `[NON_GATING]` · not price prophecy · not Track A",
        "",
        "## Summary",
        "",
        "| Cohort | tag_mode | n | hit@1 | hit@3 | status |",
        "|--------|----------|---|-------|-------|--------|",
    ]

    for label, doc in (
        ("Historical", hist_g),
        ("Historical", hist_t),
        ("Historical", hist_rag_t2),
        ("Hardset v1 uniform", hard),
        ("Hardset v2 SSOT", hard2),
        ("Hardset v2 SSOT", hard2_rag),
    ):
        if not doc:
            continue
        s = doc.get("summary") or {}
        mode = (doc.get("inputs") or {}).get("tag_mode") or s.get("tag_mode") or "?"
        policy = (doc.get("inputs") or {}).get("boost_policy") or s.get("boost_policy") or ""
        policy_note = f" · `{policy}`" if policy and label.startswith("Hardset v2") else ""
        lines.append(
            f"| {label}{policy_note} | `{mode}` | {s.get('n_non_synthetic', '—')} | "
            f"{_pct(s.get('hit_at_1_strict'))} | {_pct(s.get('hit_at_3'))} | {doc.get('status', '—')} |"
        )

    if ab:
        vo = ab.get("variants") or {}
        on = (vo.get("boost_on") or {}).get("narrative_hit_at_1_strict")
        off = (vo.get("boost_off") or {}).get("narrative_hit_at_1_strict")
        lines.extend(
            [
                "",
                "## modern_boost AB (global, narrative tier)",
                "",
                f"- boost **0.08:** narrative hit@1 **{_pct(on)}**",
                f"- boost **0.0:** narrative hit@1 **{_pct(off)}** (default)",
                f"- delta: **{ab.get('delta_narrative_hit_at_1')}**",
                f"- note: {ab.get('recommendation', '')}",
            ]
        )
    if tab:
        tv = tab.get("variants") or {}
        lines.extend(
            [
                "",
                "## tier_v1 boost AB (narrative boost blocked)",
                "",
                f"- global boost off: narrative **{_pct((tv.get('global_boost_off') or {}).get('narrative_hit_at_1_strict'))}**",
                f"- global boost on: narrative **{_pct((tv.get('global_boost_on') or {}).get('narrative_hit_at_1_strict'))}**",
                f"- tier_v1 (macro 0.08, narrative 0): narrative **{_pct((tv.get('tier_v1_macro_boost') or {}).get('narrative_hit_at_1_strict'))}**",
                f"- delta tier_v1 vs global_on: **{tab.get('delta_narrative_tier_v1_vs_global_on')}**",
                f"- note: {tab.get('recommendation', '')}",
            ]
        )
    if tier_eval:
        s = tier_eval.get("summary") or {}
        lines.extend(
            [
                "",
                "## Production eval profile (tier_v1 + gold_tags)",
                "",
                f"- hit@1 **{_pct(s.get('hit_at_1_strict'))}** · narrative **{_pct(s.get('narrative_hit_at_1_strict'))}** · macro **{_pct(s.get('macro_landmark_hit_at_1_strict'))}**",
            ]
        )

    if hcmp:
        s1 = (hcmp.get("v1_uniform_modern") or {}).get("summary") or {}
        s2 = (hcmp.get("v2_rank_top1") or {}).get("summary") or {}
        lines.extend(
            [
                "",
                "## Hardset gold mode compare (text_blind)",
                "",
                f"- v1 uniform modern: hit@1 **{_pct(s1.get('hit_at_1_strict'))}** (편향 주의)",
                f"- v2 rank_top1 gold: hit@1 **{_pct(s2.get('hit_at_1_strict'))}** (heuristic, not human)",
                f"- delta: **{hcmp.get('delta_hit_at_1_strict')}**",
            ]
        )
    if hist_ab:
        c = hist_ab.get("compare") or {}
        ms = hist_ab.get("ms_citation_contract") or {}
        lines.extend(
            [
                "",
                "## Historical tier_v2 AB (MS baseline contamination check)",
                "",
                f"- MS citation baseline (text_blind tier_v1): **{_pct(c.get('ms_citation_baseline_text_blind_tier_v1'))}**",
                f"- text_blind tier_v2: **{_pct(c.get('text_blind_tier_v2_hit_at_1_strict'))}** · Δ **{c.get('text_blind_delta_v2_minus_v1')}**",
                f"- baseline_contaminated_by_tier_v2: **`{ms.get('baseline_contaminated_by_tier_v2')}`**",
                f"- gold_tags tier_v1 → tier_v2: **{_pct(c.get('gold_tags_tier_v1_hit_at_1'))}** → **{_pct(c.get('gold_tags_tier_v2_hit_at_1'))}** (Δ {c.get('gold_tags_delta_v2_minus_v1')})",
            ]
        )
    if v2_ab or hist_v2:
        c2 = (v2_ab or {}).get("compare") or {}
        s2 = (hist_v2 or {}).get("summary") or {}
        s1_ms = (hist_t or {}).get("summary") or {}
        lines.extend(
            [
                "",
                "## text_blind_v2 B-track PoC (KO keywords + era hints · MS baseline unchanged)",
                "",
                f"- all-events v1 (MS): **{_pct(c2.get('hit_at_1_strict_v1') or s1_ms.get('hit_at_1_strict'))}**",
                f"- all-events v2 (research): **{_pct(c2.get('hit_at_1_strict_v2') or s2.get('hit_at_1_strict'))}** · Δ **{c2.get('delta_v2_minus_v1')}**",
                f"- target 15% met: **`{c2.get('target_met')}`** · ms_headline_unchanged: **`{(v2_ab or {}).get('policy', {}).get('ms_headline_unchanged')}`**",
            ]
        )
    if v2_hold:
        cmp_h = v2_hold.get("compare") or {}
        by = v2_hold.get("by_partition") or {}
        lines.extend(
            [
                "",
                "## Partition holdout (text_blind v1 vs v2)",
                "",
                "| partition | n | v1 hit@1 | v2 hit@1 | Δ |",
                "|-----------|---|----------|----------|---|",
            ]
        )
        for part in ("train_holdout", "locked_eval", "calibration"):
            block = by.get(part) or {}
            s1 = block.get("text_blind_v1_ms_baseline") or {}
            s2p = block.get("text_blind_v2_btrack_poc") or {}
            mark = " **(OOS primary)**" if part == "train_holdout" else ""
            lines.append(
                f"| `{part}`{mark} | {s1.get('n', '—')} | {_pct(s1.get('hit_at_1_strict'))} | "
                f"{_pct(s2p.get('hit_at_1_strict'))} | {block.get('delta_v2_minus_v1')} |"
            )
        lines.extend(
            [
                "",
                f"- train_holdout 15% gate: **`{cmp_h.get('train_holdout_target_15pct_met')}`**",
                f"- note: {v2_hold.get('note_ko', '')}",
            ]
        )
    if v2_hint_off:
        c3 = v2_hint_off.get("compare") or {}
        lines.extend(
            [
                "",
                "## Hint-off ablation (v2 full vs v2_no_hints · commander-approved)",
                "",
                f"- all-events: full **{_pct(c3.get('all_events_hit_at_1_full'))}** · no_hints **{_pct(c3.get('all_events_hit_at_1_no_hints'))}** · hint uplift **{_pct(c3.get('all_events_hint_uplift'))}**",
                f"- train_holdout: full **{_pct(c3.get('train_holdout_hit_at_1_full'))}** · no_hints **{_pct(c3.get('train_holdout_hit_at_1_no_hints'))}** · hint uplift **{_pct(c3.get('train_holdout_hint_uplift'))}**",
                "- MS baseline still **v1 ~6.4% only**; ablation is B-track internal lower-bound probe.",
            ]
        )
    if v2_en:
        c4 = v2_en.get("compare") or {}
        lines.extend(
            [
                "",
                "## EN headline probe (v2 · research sidecar · not live OOV)",
                "",
                f"- all-events: KO **{_pct(c4.get('all_events_hit_at_1_ko'))}** · EN **{_pct(c4.get('all_events_hit_at_1_en'))}**",
                f"- train_holdout: KO **{_pct(c4.get('train_holdout_hit_at_1_ko'))}** · EN **{_pct(c4.get('train_holdout_hit_at_1_en'))}**",
                "- Sidecar glosses only; true unseen headlines remain unmeasured off-fixture.",
            ]
        )
    if margin and margin.get("ready"):
        hi = margin.get("hardset_internal") or {}
        lines.extend(
            [
                "",
                "## Human margin report (post sign-off · internal)",
                "",
                f"- report: `reports/logos_hardset_era_human_margin_report_v1_latest.md`",
                f"- MS allowed headline: **{_pct((margin.get('ms_citation_contract') or {}).get('allowed_value'))}**",
                f"- hardset SSOT: **{_pct(hi.get('hit_at_1_strict'))}** · locked_eval **{_pct(hi.get('locked_eval_hit_at_1_strict'))}**",
            ]
        )
    if locked_cmp:
        c = locked_cmp.get("compare") or {}
        s1 = (locked_cmp.get("steps") or {}).get("text_blind_tier_v1", {}).get("summary") or {}
        s2 = (locked_cmp.get("steps") or {}).get("text_blind_tier_v2", {}).get("summary") or {}
        lines.extend(
            [
                "",
                "## Hardset tier_v2 locked_eval policy (commander-signed gold)",
                "",
                f"- text_blind tier_v1 hit@1: **{_pct(s1.get('hit_at_1_strict'))}** · locked_eval: **{_pct(c.get('locked_eval_v1'))}**",
                f"- text_blind tier_v2 hit@1: **{_pct(s2.get('hit_at_1_strict'))}** · locked_eval: **{_pct(c.get('locked_eval_v2_text_blind'))}**",
                f"- Δ v2−v1 strict: **{c.get('hit_at_1_delta_v2_minus_v1')}**",
            ]
        )
    if dmap:
        top = (dmap.get("era_ranking") or [{}])[0]
        era_id = dmap.get("primary_era_id") or top.get("era_id")
        score = dmap.get("primary_score") or top.get("score")
        band = dmap.get("confidence_band") or dmap.get("primary_confidence_band")
        lines.extend(
            [
                "",
                "## Dynamic map (live macro tags)",
                "",
                f"- primary: `{era_id}` · score **{score}** · band `{band}`",
                f"- inferred tags: `{dmap.get('inferred_regime_tags')}`",
            ]
        )

    lines.extend(
        [
            "",
            "## SSOT paths",
            "",
            "- `docs/final/artifacts/logos_chronology_era_blind_eval_v1_latest.json`",
            "- `docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json`",
            "- `docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v2_v1_latest.json` (B-track PoC · not MS)",
            "- `reports/logos_chronology_text_blind_v2_holdout_v1_latest.json`",
            "- `reports/logos_chronology_text_blind_v2_hint_off_ab_v1_latest.json`",
            "- `reports/logos_chronology_text_blind_v2_en_headline_ab_v1_latest.json`",
            "- `docs/final/artifacts/logos_chronology_hardset_text_blind_eval_v1_latest.json`",
            "- `docs/final/artifacts/logos_chronology_hardset_text_blind_v2_eval_v1_latest.json` (hardset SSOT · tier_v2_locked_eval)",
            "- `docs/final/artifacts/logos_chronology_hardset_text_blind_v2_tier_v1_baseline_eval_v1_latest.json` (compare only)",
            "- `docs/final/artifacts/logos_chronology_era_modern_boost_ab_v1_latest.json`",
            "- `docs/final/artifacts/logos_symbolic_revalidation_report_latest.json`",
            "",
            "**Caveat:** Hardset high hit@1 reflects uniform `modern_observational_field` gold + stress templates; "
            "do not cite as RAG or prophecy accuracy.",
            "",
            "Refresh: `Run-LogosChronologyEraBlindEvalFull_v1.ps1`",
            "",
        ]
    )

    cdim = _load("logos_cross_domain_interface_latest.json")
    lines.extend(
        [
            "",
            "## CDIM (cross-domain interface · separate from era hit%)",
            "",
            "- Design: `docs/final/LOGOS_CROSS_DOMAIN_INTERFACE_MAPPER_V1.md`",
            "- Digest: `reports/logos_cross_domain_interface_digest_latest.md`",
        ]
    )
    if cdim:
        lines.append(f"- CDIM `ts_utc`: `{cdim.get('ts_utc')}` · `no_verse_level_ohaeng_ingest`: `{cdim.get('no_verse_level_ohaeng_ingest')}`")
        lines.append(f"- cross_refs: `{len(cdim.get('cross_refs') or [])}` · **not** era blind metric")
    else:
        lines.append("- CDIM artifact: missing — run `Run-LogosCrossDomainInterfaceParallel_v1.ps1`")

    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {DEFAULT_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
