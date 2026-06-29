#!/usr/bin/env python3
"""PersonaDiary Logos sidebar human rubric pilot v1 [HYPO].

Runs fixed diary-text queries through sidebar candidate pools (no LLM).
Emits structural gates + empty human score slots for commander review.
Forbidden KPI: directional_hit_rate, Sharpe, prophecy vote.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_ID = "personadiary_logos_sidebar_human_rubric_v1"
VERSION = "1.0.0"
DEFAULT_QUERIES = ROOT / "docs/final/fixtures/personadiary_logos_sidebar_rubric_queries_v1.json"
DEFAULT_SIDEBAR = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json"
DEFAULT_FORBIDDEN = ROOT / "docs/final/artifacts/schemas/philosophy_lane_rag_pilot_forbidden_substrings_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_human_rubric_v1_latest.json"
REPORTS_OUT = ROOT / "reports/personadiary_logos_sidebar_human_rubric_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_logos_sidebar_human_rubric_v1.schema.json"

FORBIDDEN_PROPHECY_KEYS = {
    "directional_hit_rate",
    "directional_hit_rate_active",
    "sharpe",
    "total_return",
    "alignment_pass_rate",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _load_sidebar_builder():
    mod_path = ROOT / "scripts/build_personadiary_logos_sidebar_smoke_v1.py"
    spec = importlib.util.spec_from_file_location("pd_sidebar_build", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("sidebar_builder_import_failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _forbidden_scan(text: str, forbidden_path: Path) -> list[str]:
    doc = _read_json(forbidden_path)
    subs = doc.get("substrings") or []
    violations: list[str] = []
    lower = text.lower()
    for sub in subs:
        s = str(sub).strip()
        if s and s.lower() in lower:
            violations.append(s)
    return violations


def _rank_from_pools(sidebar_mod: Any, pools: dict[str, Any], diary_text: str) -> list[dict[str, Any]]:
    diary_tokens = sidebar_mod._tokenize(diary_text)
    philosophy_blocks = []
    for row in pools.get("logos_ann_lite") or []:
        if not isinstance(row, dict):
            continue
        philosophy_blocks.append(
            {
                "source_rail": "logos_ann_lite",
                "summary": f"logos_ann_lite hit verse_id='{row.get('verse_id')}' score={row.get('ann_score')}",
                "detail": row.get("detail") or "",
            }
        )
    ann_hits = sidebar_mod._ann_lite_hits({"blocks": philosophy_blocks}, diary_tokens)

    motif_hits = []
    for row in pools.get("graphrag_motif") or []:
        if not isinstance(row, dict):
            continue
        motif_hits.append(
            {
                "hit_type": "graphrag_motif",
                "source_rail": row.get("source_rail") or "graphrag_pilot_router",
                "node_id": row.get("node_id"),
                "assigned_symbol": row.get("assigned_symbol"),
                "score": row.get("path_score"),
                "summary": row.get("summary"),
                "match_reason": "graphrag_selected_node_rank",
            }
        )

    bridge_candidates = [c for c in (pools.get("concept_bridge") or []) if isinstance(c, dict)]
    bridge_hit = sidebar_mod._concept_bridge_hit(
        {"entries": [{"present": True, **c} for c in bridge_candidates]},
        diary_text,
    )
    return sidebar_mod._assemble_hits(ann_hits, motif_hits, bridge_hit)


def _structural_row(hits: list[dict[str, Any]], diary_text: str, forbidden_path: Path) -> dict[str, Any]:
    blob = json.dumps(hits, ensure_ascii=False)
    forbidden = _forbidden_scan(blob + diary_text, forbidden_path)
    ann_ids = [str(h.get("verse_id")) for h in hits if h.get("hit_type") == "logos_ann_lite" and h.get("verse_id")]
    grounded = sum(1 for h in hits if h.get("verse_id") or h.get("node_id") or h.get("concept_id"))
    auto_grounding_ratio = grounded / max(len(hits), 1)
    hits_ok = len(hits) == 3 and all(
        h.get("verse_id") or h.get("node_id") or h.get("concept_id") for h in hits
    )
    structural_pass = hits_ok and not forbidden
    return {
        "hits_ok": hits_ok,
        "forbidden_violations": forbidden,
        "structural_pass": structural_pass,
        "ann_lite_verse_ids": ann_ids,
        "auto_grounding_ratio": round(auto_grounding_ratio, 4),
    }


def build_rubric(
    *,
    queries_path: Path,
    sidebar_path: Path,
    forbidden_path: Path,
) -> dict[str, Any]:
    queries_doc = _read_json(queries_path)
    sidebar_doc = _read_json(sidebar_path)
    pools = sidebar_doc.get("candidate_pools") or {}
    sidebar_mod = _load_sidebar_builder()

    rows: list[dict[str, Any]] = []
    for item in queries_doc.get("queries") or []:
        if not isinstance(item, dict):
            continue
        query_id = str(item.get("query_id") or "")
        query_ko = str(item.get("query_ko") or "").strip()
        if not query_id or not query_ko:
            continue
        hits = _rank_from_pools(sidebar_mod, pools, query_ko)
        structural = _structural_row(hits, query_ko, forbidden_path)
        rows.append(
            {
                "query_id": query_id,
                "query_ko": query_ko,
                "lane_hint": item.get("lane_hint"),
                "hits": hits,
                "structural": structural,
                "human_scores": {
                    "relevance_1_5": None,
                    "citation_grounding_1_5": None,
                    "no_causal_overclaim_1_5": None,
                },
            }
        )

    n = len(rows)
    pass_n = sum(1 for r in rows if (r.get("structural") or {}).get("structural_pass"))
    structural_pass_rate = round(pass_n / n, 4) if n else 0.0
    required_ok = queries_path.is_file() and sidebar_path.is_file() and forbidden_path.is_file()
    ok = required_ok and n >= 5 and structural_pass_rate >= 0.8

    payload = {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "prophecy_vote": "none",
        "queries_fixture": _rel(queries_path),
        "sidebar_artifact": _rel(sidebar_path),
        "rows": rows,
        "summary": {
            "n_queries": n,
            "structural_pass_rate": structural_pass_rate,
            "human_rubric_mean": None,
            "human_rubric_rows_scored": 0,
            "pilot_target_n": 20,
            "note_ko": "human_rubric_mean은 지휘관이 human_scores를 채운 뒤 별도 집계. structural_pass_rate만 자동.",
        },
        "consumer_contract_ko": (
            "고정 질의 파일럿 — PersonaDiary Logos sidebar 참조 품질. "
            "structural gate만 자동; relevance/인용/과장 없음은 human_scores 수동. "
            "prophecy HR·Sharpe·Track A 금지."
        ),
        "ok": ok,
    }

    blob = json.dumps(payload)
    for key in FORBIDDEN_PROPHECY_KEYS:
        if f'"{key}"' in blob:
            payload["ok"] = False
            payload["forbidden_prophecy_key_leak"] = key
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    ap.add_argument("--sidebar", type=Path, default=DEFAULT_SIDEBAR)
    ap.add_argument("--forbidden-config", type=Path, default=DEFAULT_FORBIDDEN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reports-output", type=Path, default=REPORTS_OUT)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    if not args.sidebar.is_file():
        build = __import__("subprocess").run(
            [sys.executable, str(ROOT / "scripts/build_personadiary_logos_sidebar_smoke_v1.py"), "--strict"],
            cwd=str(ROOT),
        )
        if build.returncode != 0:
            return build.returncode

    payload = build_rubric(
        queries_path=args.queries,
        sidebar_path=args.sidebar,
        forbidden_path=args.forbidden_config,
    )

    for path in (args.output, args.reports_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.strict and not payload.get("ok"):
        print("FAIL: personadiary_logos_sidebar_human_rubric not ok", file=sys.stderr)
        return 1
    print(
        f"OK n={payload['summary']['n_queries']} "
        f"structural_pass_rate={payload['summary']['structural_pass_rate']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
