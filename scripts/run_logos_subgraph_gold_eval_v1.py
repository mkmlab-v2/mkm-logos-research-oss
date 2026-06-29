#!/usr/bin/env python3
"""Logos subgraph router gold eval v1 — Hit@k vs gold fixture ([HYPO], B-track, CPU).

Runs run_logos_subgraph_graphrag_router_v1.route() per gold query with all sidecars
(lemma, sinew, osi, theographic, gematria). Reports raw router hits only — no repair layer.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import build_logos_gold_query_eval_report_v1 as gold_ev
from run_logos_subgraph_graphrag_router_v1 import (
    DEFAULT_GEMATRIA_LEXICON,
    DEFAULT_LEMMA,
    DEFAULT_OSI_XREF,
    DEFAULT_REGISTRY,
    DEFAULT_SEED_CHAIN,
    DEFAULT_SINEW_XREF,
    DEFAULT_THEOGRAPHIC_ENTITY,
    VERSION as ROUTER_VERSION,
    _load_json,
    _load_jsonl,
    route,
)

DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_gold(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _path_gold_hits(router: dict[str, Any], gold_ids: list[str], prefixes: list[str]) -> int:
    count = 0
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps = [gold_ev.normalize_verse_ref(str(s)) for s in (path.get("steps") or [])]
        if gold_ev._match_gold(steps, gold_ids, prefixes):
            count += 1
    return count


def _evaluate_item(
    item: dict[str, Any],
    *,
    registry: dict[str, Any],
    lemma_rows: list[dict[str, Any]],
    sinew_rows: list[dict[str, Any]],
    osi_rows: list[dict[str, Any]],
    theographic_rows: list[dict[str, Any]],
    gematria_rows: list[dict[str, Any]],
    seed_chain: dict[str, Any] | None,
    k_values: list[int],
    top_bridges: int,
) -> dict[str, Any]:
    qid = str(item.get("id") or "")
    query = str(item.get("query_ko") or item.get("query_en") or "").strip()
    gold_ids = [gold_ev.normalize_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
    prefixes = [str(x) for x in (item.get("gold_verse_prefixes") or [])]
    tier = str(item.get("eval_tier") or "observational")

    router = route(
        query,
        registry=registry,
        lemma_rows=lemma_rows,
        sinew_rows=sinew_rows,
        osi_rows=osi_rows,
        theographic_rows=theographic_rows,
        gematria_lexicon_rows=gematria_rows,
        seed_chain=seed_chain,
        top_bridges=top_bridges,
    )

    router_verses = gold_ev._collect_router_verses(router)
    router_hits = gold_ev._match_gold(router_verses, gold_ids, prefixes)
    path_hits = _path_gold_hits(router, gold_ids, prefixes)

    hit_at_k: dict[str, bool] = {}
    for k in k_values:
        hit_at_k[str(k)] = gold_ev._hit_at_k(router_verses, gold_ids, prefixes, k)

    gate = item.get("gate") or {}
    gate_pass = True
    gate_reasons: list[str] = []
    if tier == "gold_required" and gate:
        if path_hits < int(gate.get("router_path_hit_min") or 0):
            gate_pass = False
            gate_reasons.append("router_path_hit_below_min")
        if len(router_hits) < int(gate.get("router_verse_hit_min") or 0):
            gate_pass = False
            gate_reasons.append("router_verse_hit_below_min")

    return {
        "id": qid,
        "query_ko": query,
        "eval_tier": tier,
        "metrics": {
            "raw": {
                "hit_at_k": hit_at_k,
                "router_gold_hits": router_hits[:12],
                "router_top_verses": router_verses[:12],
                "path_gold_hits": path_hits,
            },
            "repair_v2": None,
            "note": "raw router hits only; no repair layer",
        },
        "router": {
            "version": router.get("version") or ROUTER_VERSION,
            "bridges_matched": router.get("bridges_matched"),
            "path_count": len(router.get("paths") or []),
            "verse_count": len(router_verses),
            "theme_lanes_active": router.get("theme_lanes_active") or [],
            "sidecars": {
                "lemma_edge_hits": len(router.get("lemma_edge_hits") or []),
                "sinew_xref_hits": len(router.get("sinew_xref_hits") or []),
                "osi_xref_hits": len(router.get("osi_xref_hits") or []),
                "theographic_entity_hits": len(router.get("theographic_entity_hits") or []),
                "gematria_lexicon_hits": len(router.get("gematria_lexicon_hits") or []),
                "gematria_strongs_linked": list(
                    (router.get("gematria_lexicon_meta") or {}).get("strongs_linked") or []
                )[:8],
            },
            "policy": router.get("policy") or {},
        },
        "gate_pass": gate_pass if tier == "gold_required" else None,
        "gate_reasons": gate_reasons,
    }


def _hit_rate(rows: list[dict[str, Any]], k: int) -> float | None:
    if not rows:
        return None
    hits = sum(1 for r in rows if ((r.get("metrics") or {}).get("raw") or {}).get("hit_at_k", {}).get(str(k)))
    return round(hits / len(rows), 4)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--lemma-jsonl", type=Path, default=DEFAULT_LEMMA)
    ap.add_argument("--sinew-xref-jsonl", type=Path, default=DEFAULT_SINEW_XREF)
    ap.add_argument("--osi-xref-jsonl", type=Path, default=DEFAULT_OSI_XREF)
    ap.add_argument("--theographic-entity-jsonl", type=Path, default=DEFAULT_THEOGRAPHIC_ENTITY)
    ap.add_argument("--gematria-lexicon-jsonl", type=Path, default=DEFAULT_GEMATRIA_LEXICON)
    ap.add_argument("--seed-chain-json", type=Path, default=DEFAULT_SEED_CHAIN)
    ap.add_argument("--top-bridges", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="Evaluate first N gold items only (0=all)")
    ap.add_argument("--disable-lemma-sidecar", action="store_true")
    ap.add_argument("--disable-sinew-sidecar", action="store_true")
    ap.add_argument("--disable-osi-sidecar", action="store_true")
    ap.add_argument("--disable-theographic-sidecar", action="store_true")
    ap.add_argument("--disable-gematria-sidecar", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any gold_required gate fails")
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json

    gold_doc = _read_gold(gold_path)
    if gold_doc.get("schema") != "logos_gold_query_eval_v1":
        print(f"[ERROR] invalid gold schema: {gold_path}", file=sys.stderr)
        return 2

    registry = _load_json(args.registry_json)
    if not registry:
        print(f"[ERROR] missing registry: {args.registry_json}", file=sys.stderr)
        return 2

    lemma_rows = [] if args.disable_lemma_sidecar else _load_jsonl(args.lemma_jsonl)
    sinew_rows = (
        []
        if args.disable_sinew_sidecar
        else (_load_jsonl(args.sinew_xref_jsonl) if args.sinew_xref_jsonl.is_file() else [])
    )
    osi_rows = (
        []
        if args.disable_osi_sidecar
        else (_load_jsonl(args.osi_xref_jsonl) if args.osi_xref_jsonl.is_file() else [])
    )
    theographic_rows = (
        []
        if args.disable_theographic_sidecar
        else (
            _load_jsonl(args.theographic_entity_jsonl) if args.theographic_entity_jsonl.is_file() else []
        )
    )
    gematria_rows = (
        []
        if args.disable_gematria_sidecar
        else (_load_jsonl(args.gematria_lexicon_jsonl) if args.gematria_lexicon_jsonl.is_file() else [])
    )
    seed_chain = _load_json(args.seed_chain_json)

    k_values = [int(x) for x in (gold_doc.get("k_at") or [1, 3, 8])]
    items_in = [x for x in (gold_doc.get("items") or []) if isinstance(x, dict)]
    if args.limit > 0:
        items_in = items_in[: args.limit]

    rows = [
        _evaluate_item(
            it,
            registry=registry,
            lemma_rows=lemma_rows,
            sinew_rows=sinew_rows,
            osi_rows=osi_rows,
            theographic_rows=theographic_rows,
            gematria_rows=gematria_rows,
            seed_chain=seed_chain,
            k_values=k_values,
            top_bridges=args.top_bridges,
        )
        for it in items_in
    ]

    required = [r for r in rows if r.get("eval_tier") == "gold_required"]
    all_required_pass = all(r.get("gate_pass") for r in required)
    hit_rates = {str(k): _hit_rate(rows, k) for k in k_values}

    doc = {
        "schema": "logos_subgraph_gold_eval_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "lane": "logos_subgraph_router_gold_cpu",
        "gpu_used": False,
        "metric_layer": "raw",
        "repair_layer_applied": False,
        "router_version": ROUTER_VERSION,
        "gold_fixture": (
            str(gold_path.relative_to(ROOT)) if gold_path.is_relative_to(ROOT) else str(gold_path)
        ),
        "sidecars": {
            "lemma_jsonl": str(args.lemma_jsonl),
            "sinew_xref_jsonl": str(args.sinew_xref_jsonl),
            "osi_xref_jsonl": str(args.osi_xref_jsonl),
            "theographic_entity_jsonl": str(args.theographic_entity_jsonl),
            "gematria_lexicon_jsonl": str(args.gematria_lexicon_jsonl),
            "lemma_disabled": args.disable_lemma_sidecar,
            "sinew_disabled": args.disable_sinew_sidecar,
            "osi_disabled": args.disable_osi_sidecar,
            "theographic_disabled": args.disable_theographic_sidecar,
            "gematria_disabled": args.disable_gematria_sidecar,
            "sinew_edges": len(sinew_rows),
            "osi_edges": len(osi_rows),
            "theographic_edges": len(theographic_rows),
            "gematria_entries": len(gematria_rows),
        },
        "summary": {
            "items_evaluated": len(rows),
            "gold_required_count": len(required),
            "gold_required_all_pass": all_required_pass,
            "hit_at_k_rates": hit_rates,
            "mean_path_gold_hits": round(
                sum(
                    ((r.get("metrics") or {}).get("raw") or {}).get("path_gold_hits") or 0 for r in rows
                )
                / max(len(rows), 1),
                4,
            ),
            "path_gold_hit_item_rate": round(
                sum(
                    1
                    for r in rows
                    if (((r.get("metrics") or {}).get("raw") or {}).get("path_gold_hits") or 0) >= 1
                )
                / max(len(rows), 1),
                4,
            ),
            "mean_router_gold_hits": round(
                sum(
                    len(((r.get("metrics") or {}).get("raw") or {}).get("router_gold_hits") or [])
                    for r in rows
                )
                / max(len(rows), 1),
                4,
            ),
        },
        "rows": rows,
        "reproduce": (
            "py scripts/run_logos_subgraph_gold_eval_v1.py "
            f"--gold-json {gold_path.relative_to(ROOT) if gold_path.is_relative_to(ROOT) else gold_path}"
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    print(
        json.dumps(
            {
                "ok": True,
                "items_evaluated": len(rows),
                "gold_required_all_pass": all_required_pass,
                "hit_at_k_rates": hit_rates,
            },
            ensure_ascii=False,
        )
    )

    if args.strict and not all_required_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
