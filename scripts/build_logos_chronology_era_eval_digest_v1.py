#!/usr/bin/env python3
"""One-page operator digest for era blind eval artifacts ([HYPO], NON_GATING)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ROOT / "reports/logos_chronology_era_blind_eval_digest_v1_latest.md"


def _load(name: str) -> dict[str, Any] | None:
    p = ART / name
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
    hcmp = _load("logos_chronology_hardset_gold_mode_compare_v1_latest.json")
    ab = _load("logos_chronology_era_modern_boost_ab_v1_latest.json")
    tab = _load("logos_chronology_era_tier_boost_ab_v1_latest.json")
    tier_eval = _load("logos_chronology_era_blind_eval_tier_v1_latest.json")
    dmap = _load("logos_chronology_dynamic_map_v1_latest.json")

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
        ("Hardset v1 uniform", hard),
        ("Hardset v2 rank gold", hard2),
    ):
        if not doc:
            continue
        s = doc.get("summary") or {}
        mode = (doc.get("inputs") or {}).get("tag_mode") or s.get("tag_mode") or "?"
        lines.append(
            f"| {label} | `{mode}` | {s.get('n_non_synthetic', '—')} | "
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
            "- `docs/final/artifacts/logos_chronology_hardset_text_blind_eval_v1_latest.json`",
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
