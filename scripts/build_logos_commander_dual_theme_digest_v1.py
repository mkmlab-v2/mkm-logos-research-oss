#!/usr/bin/env python3
"""Single commander digest MD for dan_aramaic + john_1_logos themed reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs/final/artifacts"
OUT_DEFAULT = REPORTS / "logos_track_b_commander_dual_theme_digest_latest.md"
THEMES = (
    ("dan_aramaic", "다니엘 2장 아람어"),
    ("john_1_logos", "요한복음 1장 로고스"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_optional(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return _load(path)
    except (json.JSONDecodeError, OSError):
        return None


def _dual_backend_row(theme_id: str, dual_doc: dict | None) -> dict | None:
    if not dual_doc:
        return None
    for row in dual_doc.get("themes") or []:
        if row.get("theme_id") == theme_id:
            return row
    return None


def _graphrag_row(theme_id: str, audit_doc: dict | None) -> dict | None:
    if not audit_doc:
        return None
    for row in audit_doc.get("themes") or []:
        if row.get("theme_id") == theme_id:
            return row
    return None


def render() -> str:
    dual_doc = _load_optional(REPORTS / "logos_themed_retrieval_dual_backend_v1_latest.json")
    graphrag_audit = _load_optional(REPORTS / "logos_themed_graphrag_seed_retrieval_v1_latest.json")
    xref_manifest = _load_optional(REPORTS / "logos_themed_xref_subgraph_v1_latest.json")
    b2b_summary = _load_optional(ART / "logos_b2b_proposal_master_summary_v1_latest.json")
    b2b_verifier = _load_optional(REPORTS / "logos_b2b_proposal_goal_verifier_v1_latest.json")
    p5_gate = _load_optional(ART / "p5_manuscript_integrity_gate_v1_latest.json")
    p5_audit = _load_optional(REPORTS / "manuscript_integrity_audit_11q5_psalms_commander_v1_latest.json")
    map_4q = _load_optional(REPORTS / "dss_4q_ps5_line_witness_map_v1_latest.json")
    post_gate = _load_optional(ART / "entry_13_post_promotion_gate_v1_latest.json")
    p8_gate = _load_optional(ART / "logos_bible_rail_completion_gate_v1_latest.json")
    reg4 = _load_optional(REPORTS / "shadow_4q_ps5_witness_registry_v1_latest.json")
    op_board = _load_optional(REPORTS / "dss_line_witness_verification_operator_board_v1_latest.json")

    lines = [
        "# Logos Track B — 듀얼 테마 지휘관 다이제스트",
        "",
        "[TRACK B / HYPO] · [연구용: 최종 판단은 지휘관 대기]",
        "",
        f"> 생성 `{_utc_now()}` · NON_GATING · A-track 자동 트리거 금지",
        "",
    ]
    if graphrag_audit:
        sm = graphrag_audit.get("summary") or {}
        lines += [
            "### GraphRAG 시드 회수 (테마 앵커)",
            "",
            f"- organic: `{sm.get('seed_hits_organic')}` · xref 후: `{sm.get('seed_hits_full')}`",
            f"- xref edges: `{xref_manifest.get('total_edges') if xref_manifest else 'n/a'}`",
            "",
        ]
    if b2b_summary and b2b_verifier:
        lines += [
            "### B2B 논리 이식 (광명백제 · 부록 전용)",
            "",
            f"- verifier: `{b2b_verifier.get('verdict')}` · promoted: `{b2b_summary.get('promoted')}`",
            f"- claims: **{b2b_summary.get('promoted_claim_count', len(b2b_summary.get('promoted_claims') or []))}**",
            "",
        ]
    if p5_gate:
        sm4 = (map_4q or {}).get("summary") or {}
        reg_sm = (reg4 or {}).get("summary") or {}
        lines += [
            "### 원고 무결성 (ENTRY_12/13 · P5–P8)",
            "",
            f"- P5 gate: `{p5_gate.get('gate_ok')}` · promotion_ok: `{op_board.get('promotion_ok') if op_board else 'n/a'}`",
            f"- ENTRY_12: **mt_only** · 11Q5 bench: **hypothesis_retired**",
            f"- ENTRY_13 4Q provisional: **{sm4.get('provisional_lexical_anchor_rows', 'n/a')}** · commander verified: **{reg_sm.get('commander_verified_rows', 0)}**",
            f"- shadow anchor: **{(reg4 or {}).get('shadow_verse_anchor', 'n/a')}** · post-promotion gate: `{(post_gate or {}).get('gate_ok')}`",
            f"- P8/P9 bible rail: **{(p8_gate or {}).get('bible_rail_status', 'n/a')}** · completion gate: `{(p8_gate or {}).get('gate_ok')}`",
            f"- auto_verified: **{(op_board or {}).get('auto_verified_total', 0)}** · SEND_GATE: **HOLD**",
            "",
        ]
        if p5_audit:
            for f in (p5_audit.get("findings") or [])[:4]:
                lines.append(f"- {f.get('id')}: {f.get('claim')} → `{f.get('status')}`")
            lines.append("")
    for theme_id, title in THEMES:
        locked_path = ART / f"logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
        md_path = REPORTS / f"logos_track_b_commander_deep_report_{theme_id}_latest.md"
        router_path = ART / f"logos_subgraph_graphrag_router_{theme_id}_latest.json"
        lines += [f"## {title} (`{theme_id}`)", ""]
        if not locked_path.is_file():
            lines += ["- *(증류 없음)*", ""]
            continue
        doc = _load(locked_path)
        narr = doc.get("distill_narrative_stub_ko") or {}
        body = str(narr.get("body_ko") or "").strip()
        lines += [
            f"- evidence_refs: **{len(doc.get('evidence_refs') or [])}**",
            f"- graph_paths: **{len(doc.get('graph_paths') or [])}**",
            f"- citation_locked: **{(doc.get('citation_lock') or {}).get('locked_count')}**",
            f"- llm_invoked: `{narr.get('llm_invoked')}` · citation_valid: `{narr.get('citation_valid')}`",
            f"- 상세 MD: `{md_path.relative_to(ROOT).as_posix()}`",
            "",
        ]
        dual_row = _dual_backend_row(theme_id, dual_doc)
        if dual_row:
            h = dual_row.get("hash_stub_v1") or {}
            st = dual_row.get("sentence_transformers") or {}
            delta = dual_row.get("delta_recall_st_minus_hash")
            lines += [
                "### retrieval recall@5",
                "",
                f"- hash_stub: `{h.get('anchor_recall_at_k')}` · ST: `{st.get('anchor_recall_at_k')}` · delta: `{delta}`",
                "",
            ]
        gr = _graphrag_row(theme_id, graphrag_audit)
        if gr:
            lines += [
                "### GraphRAG vs distill seeds",
                "",
                f"- organic overlap: `{gr.get('seed_hit_organic')}` · xref 후: `{gr.get('seed_hit_full')}`",
                f"- xref neighbors: **{gr.get('xref_neighbor_count', 0)}**",
                "",
            ]
        if router_path.is_file():
            router = _load(router_path)
            enrich = router.get("xref_enrichment") or {}
            if enrich:
                lines += [
                    f"- router verse_ids: **{len(router.get('verse_ids') or [])}** (graphrag `{enrich.get('router_verse_count', '?')}` + xref `{enrich.get('neighbor_count', 0)}`)",
                    "",
                ]
        if body:
            lines += ["### 증류 서술 (발췌)", "", body[:1200] + ("…" if len(body) > 1200 else ""), ""]
    lines += [
        "---",
        "재현: `py scripts/run_logos_track_b_auto_continue_v1.py` (원클릭)",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
