#!/usr/bin/env python3
"""KOSPI 4-lens GraphRAG fusion pack — Field + Logos + Myeongni + Sasang [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOGOS_GRAPHRAG = ROOT / "reports/logos_graphrag_kospi9000_excess_v1_latest.json"
DEFAULT_LOGOS_CROSSWALK = ROOT / "reports/kospi_june2026_logos_anchor_crosswalk_v1_latest.json"
DEFAULT_LOGOS_LENS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"
DEFAULT_MYEONGNI_LENS = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_SASANG_LENS = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
DEFAULT_OVERNIGHT = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"
DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_CALENDAR = ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json"
DEFAULT_CROSS_FUSION = ROOT / "docs/final/artifacts/cross_lens_rag_fusion_latest.json"
DEFAULT_MYEONGNI_CORPUS_ROUTER = ROOT / "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_LOGOS_TIER2 = ROOT / "reports/logos_lens_conflict_digest_tier2_v1_latest.json"
DEFAULT_MYEONGNI_TIER2 = ROOT / "reports/myeongni_lens_tier2_v1_latest.json"
DEFAULT_SASANG_TIER2 = ROOT / "reports/sasang_lens_veto_tier2_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.md"

SEED_MY = ROOT / "data/btrack/lens_graphrag/kospi_tail_myeongni_hypo_v1.seed.json"
SEED_SA = ROOT / "data/btrack/lens_graphrag/kospi_tail_sasang_hypo_v1.seed.json"
SEED_FI = ROOT / "data/btrack/lens_graphrag/kospi_tail_field_events_hypo_v1.seed.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _score(doc: dict[str, Any] | None) -> tuple[float, float, str]:
    if not doc:
        return 0.0, 0.0, "neutral"
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    s = float(scores.get("direction_score") or 0.0)
    c = max(0.0, min(1.0, float(scores.get("confidence") or 0.0)))
    if s > 0.05:
        sign = "bull"
    elif s < -0.05:
        sign = "bear"
    else:
        sign = "neutral"
    return s, c, sign


def _load_seed(path: Path) -> dict[str, Any] | None:
    return _read(path)


def _latest_eval_row(eval_doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not eval_doc:
        return None
    rows = eval_doc.get("rows")
    if not isinstance(rows, list) or not rows:
        return None
    return rows[-1] if isinstance(rows[-1], dict) else None


def _calendar_forward(calendar: dict[str, Any] | None, n: int = 4) -> list[dict[str, Any]]:
    if not calendar:
        return []
    days = calendar.get("rows")
    if not isinstance(days, list):
        return []
    out: list[dict[str, Any]] = []
    for row in days:
        if not isinstance(row, dict):
            continue
        if row.get("status") == "pending":
            prop = row.get("kospi_index_prophecy") if isinstance(row.get("kospi_index_prophecy"), dict) else {}
            out.append(
                {
                    "session_date": row.get("session_date"),
                    "direction_ko": row.get("predicted_direction_ko"),
                    "close_mid": prop.get("predicted_close_mid"),
                }
            )
        if len(out) >= n:
            break
    return out


def _logos_slice(graphrag: dict[str, Any] | None, crosswalk: dict[str, Any] | None, lens: dict[str, Any] | None) -> dict[str, Any]:
    score, conf, sign = _score(lens)
    paths = []
    if graphrag and isinstance(graphrag.get("paths"), list):
        for p in graphrag["paths"][:4]:
            if isinstance(p, dict):
                steps = p.get("steps") or []
                verse = steps[-1] if steps else None
                paths.append({"verse_or_step": verse, "note_ko": p.get("note_ko")})
    topics = []
    if crosswalk and isinstance(crosswalk.get("anchors"), list):
        for a in crosswalk["anchors"][:5]:
            if isinstance(a, dict):
                topics.append(
                    {
                        "topic_id": a.get("topic_id"),
                        "weight": a.get("weight"),
                        "graphrag_ref": a.get("graphrag_ref"),
                    }
                )
    return {
        "lens_id": "logos",
        "non_gating": True,
        "direction_score": score,
        "confidence": conf,
        "direction_sign": sign,
        "graphrag_query": (graphrag or {}).get("query"),
        "top_paths": paths,
        "crosswalk_topics": topics,
        "seed_pointer": "reports/logos_graphrag_kospi9000_excess_v1_latest.json",
    }


def _lens_from_seed_and_disk(
    seed: dict[str, Any] | None,
    lens_doc: dict[str, Any] | None,
    *,
    lens_id: str,
    graphrag_router: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score, conf, sign = _score(lens_doc)
    nodes = []
    gpaths = []
    if seed:
        for n in seed.get("anchor_nodes") or []:
            if isinstance(n, dict):
                nodes.append({"node_id": n.get("node_id"), "label_ko": n.get("label_ko")})
        for p in seed.get("graph_paths") or []:
            if isinstance(p, dict):
                gpaths.append({"path_id": p.get("path_id"), "note_ko": p.get("note_ko")})
    out: dict[str, Any] = {
        "lens_id": lens_id,
        "non_gating": True,
        "horizon_contract": (seed or {}).get("horizon_contract"),
        "direction_score": score,
        "confidence": conf,
        "direction_sign": sign,
        "anchor_nodes": nodes,
        "graph_paths": gpaths,
        "query_ko": (seed or {}).get("query_ko"),
    }
    if graphrag_router is not None:
        out["graphrag_router"] = graphrag_router
    return out


def _myeongni_graphrag_router_slice(router_path: Path) -> dict[str, Any] | None:
    doc = _read(router_path)
    if not doc:
        return None
    paths = doc.get("paths") if isinstance(doc.get("paths"), list) else []
    top_paths: list[dict[str, Any]] = []
    for p in paths[:3]:
        if not isinstance(p, dict):
            continue
        top_paths.append(
            {
                "path_id": p.get("path_id"),
                "match_score": p.get("match_score"),
                "note_ko": p.get("note_ko"),
                "chunk_id": p.get("chunk_id"),
            }
        )
    return {
        "pointer": str(router_path.as_posix()),
        "schema": doc.get("schema"),
        "query": doc.get("query"),
        "chunk_hits": doc.get("chunk_hits"),
        "paths_count": len(paths),
        "top_paths": top_paths,
        "send_gate": (doc.get("policy") or {}).get("send_gate", "HOLD"),
    }


def _field_slice(
    seed: dict[str, Any] | None,
    eval_row: dict[str, Any] | None,
    overnight: dict[str, Any] | None,
) -> dict[str, Any]:
    actual_close = eval_row.get("actual_close") if eval_row else None
    actual_dir = eval_row.get("actual_direction") if eval_row else None
    ret_pct = eval_row.get("daily_return_pct") if eval_row else None
    composite = overnight.get("composite_tilt") if overnight else None
    nodes = []
    gpaths = []
    if seed:
        for n in seed.get("anchor_nodes") or []:
            if isinstance(n, dict):
                nodes.append({"node_id": n.get("node_id"), "label_ko": n.get("label_ko")})
        for p in seed.get("graph_paths") or []:
            if isinstance(p, dict):
                gpaths.append({"path_id": p.get("path_id"), "note_ko": p.get("note_ko")})
    if actual_dir == "bear" and ret_pct is not None and float(ret_pct) <= -5.0:
        field_sign = "bear"
        field_score = -0.7
    elif actual_dir == "bull":
        field_sign = "bull"
        field_score = 0.5
    else:
        field_sign = "neutral"
        field_score = 0.0
    return {
        "layer": "field",
        "gating_eligible": True,
        "direction_sign": field_sign,
        "direction_score": field_score,
        "observed_close": actual_close,
        "daily_return_pct": ret_pct,
        "overnight_composite_tilt": composite,
        "event_nodes": nodes,
        "graph_paths": gpaths,
        "note_ko": "Field = regime_map·OHLCV·overnight — 유일한 게이팅 후보 층",
    }


def _conflict_and_final(
    field: dict[str, Any],
    logos: dict[str, Any],
    myeongni: dict[str, Any],
    sasang: dict[str, Any],
    *,
    forward_days: list[dict[str, Any]],
) -> dict[str, Any]:
    lens_signs = {
        "logos": logos.get("direction_sign"),
        "myeongni": myeongni.get("direction_sign"),
        "sasang": sasang.get("direction_sign"),
    }
    field_sign = field.get("direction_sign")
    bear_count = sum(1 for s in lens_signs.values() if s == "bear")
    bull_count = sum(1 for s in lens_signs.values() if s == "bull")
    conflicts: list[str] = []
    if field_sign == "bear" and bull_count >= 2:
        conflicts.append("field_bear_vs_lens_bull_majority")
    if logos.get("direction_sign") == "bear" and myeongni.get("direction_sign") == "bull":
        conflicts.append("logos_bear_myeongni_bull")
    if sasang.get("direction_sign") != "neutral" and field_sign == "bear":
        conflicts.append("sasang_not_neutral_on_shock_day")
    # 6/23 pattern: v2 said neutral, field+logos bear
    final = "WATCH"
    advisory_ko = "Field tail shock 우선 · 8460대 재앵커 · 이번 주 9000 회복 비우세"
    if field_sign == "bear" and bear_count >= 1:
        final = "WATCH"
        advisory_ko = (
            "급락 Field 앵커 + Logos excess_unwind 정합 — 단기 반등 가능하나 "
            "9,000 재돌파는 밴드·WF 모두 비우세. hold·관측."
        )
    return {
        "lens_signs": lens_signs,
        "field_sign": field_sign,
        "conflict_ids": conflicts,
        "forward_calendar_snippet": forward_days,
        "final_action": final,
        "send_gate": "HOLD",
        "advisory_ko": advisory_ko,
    }


def _render_md(doc: dict[str, Any]) -> str:
    f = doc.get("field") or {}
    logos = doc.get("lenses", {}).get("logos") or {}
    my = doc.get("lenses", {}).get("myeongni") or {}
    sa = doc.get("lenses", {}).get("sasang") or {}
    res = doc.get("fusion_resolution") or {}
    lines = [
        "# KOSPI 4-Lens GraphRAG Fusion [HYPO]",
        "",
        f"**Generated:** {doc.get('generated_at_utc')} · **B-track** · `send_gate: HOLD`",
        "",
        "## Field (게이팅 후보)",
        "",
        f"- 관측 종가: **{f.get('observed_close')}** · 일간: **{f.get('daily_return_pct')}%**",
        f"- overnight: `{f.get('overnight_composite_tilt')}` · sign: **{f.get('direction_sign')}**",
        "",
        "## Lens — 성경 (Logos) `[NON_GATING]`",
        "",
        f"- sign: **{logos.get('direction_sign')}** (score {logos.get('direction_score')})",
        f"- query: {logos.get('graphrag_query')}",
    ]
    for p in logos.get("top_paths") or []:
        lines.append(f"  - {p.get('verse_or_step')}: {p.get('note_ko')}")
    lines.extend(
        [
            "",
            "## Lens — 명리 `[NON_GATING]`",
            "",
            f"- sign: **{my.get('direction_sign')}** · horizon: {my.get('horizon_contract')}",
            f"- {my.get('query_ko')}",
            "",
            "## Lens — 사상 `[NON_GATING]`",
            "",
            f"- sign: **{sa.get('direction_sign')}** · horizon: {sa.get('horizon_contract')}",
            f"- {sa.get('query_ko')}",
            "",
            "## Conflict → Final",
            "",
            f"- conflicts: `{', '.join(res.get('conflict_ids') or []) or 'none'}`",
            f"- **final_action:** {res.get('final_action')}",
            f"- {res.get('advisory_ko')}",
            "",
            "### Forward snippet (v2 calendar)",
            "",
        ]
    )
    for row in res.get("forward_calendar_snippet") or []:
        lines.append(f"- {row.get('session_date')}: {row.get('direction_ko')} · mid {row.get('close_mid')}")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```powershell",
            "py scripts/run_kospi_four_lens_graphrag_fusion_chain_v1.py",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _tier2_summary(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    slim: dict[str, Any] = {
        "schema": doc.get("schema"),
        "tier2_role": doc.get("tier2_role"),
        "send_gate": doc.get("send_gate"),
    }
    for k in (
        "policy",
        "holdout_metrics",
        "promotion_candidate",
        "excess_unwind_routes",
        "conflict_ids",
        "corpus_paths",
        "force_hold",
        "veto_reason_codes",
        "band_widen_only",
        "operator_note_ko",
        "advisory_ko",
    ):
        if k in doc:
            slim[k] = doc[k]
    return slim


def build_pack(
    *,
    logos_graphrag: Path,
    logos_crosswalk: Path,
    logos_lens: Path,
    myeongni_lens: Path,
    sasang_lens: Path,
    overnight: Path,
    eval_json: Path,
    calendar_json: Path,
    cross_fusion: Path,
    seed_my: Path,
    seed_sa: Path,
    seed_fi: Path,
    myeongni_corpus_router: Path,
    field_tier2: Path | None = None,
    logos_tier2: Path | None = None,
    myeongni_tier2: Path | None = None,
    sasang_tier2: Path | None = None,
) -> dict[str, Any]:
    logos_gr = _read(logos_graphrag)
    logos_cw = _read(logos_crosswalk)
    logos_l = _read(logos_lens)
    my_l = _read(myeongni_lens)
    sa_l = _read(sasang_lens)
    ov = _read(overnight)
    ev = _read(eval_json)
    cal = _read(calendar_json)
    cross = _read(cross_fusion)

    eval_row = _latest_eval_row(ev)
    field = _field_slice(_load_seed(seed_fi), eval_row, ov)
    logos = _logos_slice(logos_gr, logos_cw, logos_l)
    my_router = _myeongni_graphrag_router_slice(myeongni_corpus_router)
    myeongni = _lens_from_seed_and_disk(
        _load_seed(seed_my), my_l, lens_id="myeongni", graphrag_router=my_router
    )
    sasang = _lens_from_seed_and_disk(_load_seed(seed_sa), sa_l, lens_id="sasang")
    ft2 = _tier2_summary(_read(field_tier2)) if field_tier2 else None
    lt2 = _tier2_summary(_read(logos_tier2)) if logos_tier2 else None
    mt2 = _tier2_summary(_read(myeongni_tier2)) if myeongni_tier2 else None
    st2 = _tier2_summary(_read(sasang_tier2)) if sasang_tier2 else None
    if ft2:
        field["tier2"] = ft2
    if lt2:
        logos["tier2"] = lt2
    if mt2:
        myeongni["tier2"] = mt2
    if st2:
        sasang["tier2"] = st2
    forward = _calendar_forward(cal, 4)
    resolution = _conflict_and_final(field, logos, myeongni, sasang, forward_days=forward)

    return {
        "schema": "kospi_four_lens_graphrag_fusion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating_lenses": ["logos", "myeongni", "sasang"],
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "session_anchor": (eval_row or {}).get("session_date"),
        "field": field,
        "lenses": {"logos": logos, "myeongni": myeongni, "sasang": sasang},
        "fusion_resolution": resolution,
        "upstream_pointers": {
            "logos_graphrag": str(logos_graphrag.as_posix()),
            "logos_crosswalk": str(logos_crosswalk.as_posix()),
            "cross_lens_rag_fusion": str(cross_fusion.as_posix()) if cross else None,
            "eval": str(eval_json.as_posix()),
            "field_event_graph": "reports/field_kospi_event_graph_v1_latest.json",
            "myeongni_corpus_router": str(myeongni_corpus_router.as_posix())
            if my_router
            else None,
            "field_tier2": str(field_tier2.as_posix()) if field_tier2 and ft2 else None,
            "logos_tier2": str(logos_tier2.as_posix()) if logos_tier2 and lt2 else None,
            "myeongni_tier2": str(myeongni_tier2.as_posix()) if myeongni_tier2 and mt2 else None,
            "sasang_tier2": str(sasang_tier2.as_posix()) if sasang_tier2 and st2 else None,
        },
        "cross_lens_rag_signal": (cross or {}).get("signal_light"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logos-graphrag", type=Path, default=DEFAULT_LOGOS_GRAPHRAG)
    ap.add_argument("--logos-crosswalk", type=Path, default=DEFAULT_LOGOS_CROSSWALK)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--myeongni-lens", type=Path, default=DEFAULT_MYEONGNI_LENS)
    ap.add_argument("--sasang-lens", type=Path, default=DEFAULT_SASANG_LENS)
    ap.add_argument("--overnight", type=Path, default=DEFAULT_OVERNIGHT)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--calendar-json", type=Path, default=DEFAULT_CALENDAR)
    ap.add_argument("--cross-fusion", type=Path, default=DEFAULT_CROSS_FUSION)
    ap.add_argument("--seed-myeongni", type=Path, default=SEED_MY)
    ap.add_argument("--seed-sasang", type=Path, default=SEED_SA)
    ap.add_argument("--seed-field", type=Path, default=SEED_FI)
    ap.add_argument(
        "--myeongni-corpus-router",
        type=Path,
        default=DEFAULT_MYEONGNI_CORPUS_ROUTER,
        help="Myeongni corpus GraphRAG router JSON (best-effort attach under lenses.myeongni).",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument(
        "--attach-tier2",
        action="store_true",
        help="Attach per-lens Tier2 snapshots when present on disk.",
    )
    args = ap.parse_args(argv)

    field_t2 = DEFAULT_FIELD_TIER2 if args.attach_tier2 else None
    logos_t2 = DEFAULT_LOGOS_TIER2 if args.attach_tier2 else None
    myeongni_t2 = DEFAULT_MYEONGNI_TIER2 if args.attach_tier2 else None
    sasang_t2 = DEFAULT_SASANG_TIER2 if args.attach_tier2 else None

    doc = build_pack(
        logos_graphrag=args.logos_graphrag,
        logos_crosswalk=args.logos_crosswalk,
        logos_lens=args.logos_lens,
        myeongni_lens=args.myeongni_lens,
        sasang_lens=args.sasang_lens,
        overnight=args.overnight,
        eval_json=args.eval_json,
        calendar_json=args.calendar_json,
        cross_fusion=args.cross_fusion,
        seed_my=args.seed_myeongni,
        seed_sa=args.seed_sasang,
        seed_fi=args.seed_field,
        myeongni_corpus_router=args.myeongni_corpus_router,
        field_tier2=field_t2,
        logos_tier2=logos_t2,
        myeongni_tier2=myeongni_t2,
        sasang_tier2=sasang_t2,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(_render_md(doc), encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_four_lens_graphrag_fusion_v1_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(args.out_json),
                "out_md": str(args.out_md),
                "final_action": doc["fusion_resolution"]["final_action"],
                "conflicts": doc["fusion_resolution"]["conflict_ids"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
