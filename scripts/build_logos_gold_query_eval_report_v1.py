#!/usr/bin/env python3
"""Logos gold-query retrieval eval — CPU-only, reads existing Magic Orb artifacts.

Compares token router vs ANN-lite Hit@k against gold verse set.
Does not load GPU models or touch Nemotron/WSL paths.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_gold_query_eval_v1_latest.json"
REPORT_DIR = ROOT / "reports/magic_orb_insight_by_query"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse_verse_ref_slug(body: str) -> str:
    """verse_ref:jeremiah_1_10 → Jer.1.10; daniel_5_25_28 → Dan.5.25."""
    parts = body.split("_")
    if len(parts) >= 4 and parts[-1].isdigit() and parts[-2].isdigit() and parts[-3].isdigit():
        book = "_".join(parts[:-3])
        return f"{_title_book(book)}.{parts[-3]}.{parts[-2]}"
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        book = "_".join(parts[:-2])
        return f"{_title_book(book)}.{parts[-2]}.{parts[-1]}"
    return body.replace("_", ".")


def _parse_node_verse_slug(body: str) -> str:
    """node_verse body: john_19_34 → John.19.34; lamentations_3_22_23 → Lam.3.22."""
    parts = body.split("_")
    if len(parts) >= 4 and parts[-1].isdigit() and parts[-2].isdigit() and parts[-3].isdigit():
        book = "_".join(parts[:-3])
        return f"{_title_book(book)}.{parts[-3]}.{parts[-2]}"
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        book = "_".join(parts[:-2])
        return f"{_title_book(book)}.{parts[-2]}.{parts[-1]}"
    if len(parts) == 2 and parts[-1].isdigit():
        m = re.match(r"^([a-z0-9]+?)(\d+)$", parts[0], flags=re.IGNORECASE)
        if m:
            return f"{_title_book(m.group(1))}.{m.group(2)}.{parts[1]}"
    return body.replace("_", ".")


def normalize_verse_ref(raw: str) -> str:
    """Collapse node_verse_john_19_34, greek::John.19.34 → John.19.34."""
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.startswith("verse_ref:"):
        s = _parse_verse_ref_slug(s.split(":", 1)[1])
    elif s.startswith("vr_"):
        s = _parse_verse_ref_slug(s[3:])
    if s.lower().startswith("verse:"):
        s = s.split(":", 1)[1]
    if s.lower().startswith("ref:"):
        s = s.split(":", 1)[1]
    if s.startswith("node:verse_ref:"):
        s = s[len("node:verse_ref:") :]
        parts = s.split("_")
        if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
            book = "_".join(parts[:-2])
            return f"{_title_book(book)}.{parts[-2]}.{parts[-1]}"
    if s.startswith("node_verse_"):
        return _parse_node_verse_slug(s[len("node_verse_") :])
    if s.startswith("node:verse_"):
        return _parse_node_verse_slug(s[len("node:verse_") :])
    if s.startswith("verse_"):
        return _parse_node_verse_slug(s[len("verse_") :])
    if "::" in s:
        s = s.split("::", 1)[1]
    m = re.match(r"^([A-Za-z0-9]+)_(\d+)\.(\d+)\.(\d+)$", s)
    if m:
        return f"{_title_book(m.group(1))}.{m.group(2)}.{m.group(3)}"
    m = re.match(r"^([a-z]+)(\d+)\.(\d+)$", s, flags=re.IGNORECASE)
    if m:
        return f"{_title_book(m.group(1))}.{m.group(2)}.{m.group(3)}"
    m = re.match(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)-", s)
    if m:
        return f"{_title_book(m.group(1))}.{m.group(2)}.{m.group(3)}"
    # Full book names from bridge nodes: Jeremiah.31.33 → Jer.31.33
    m = re.match(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)$", s)
    if m:
        book = _title_book(m.group(1))
        return f"{book}.{m.group(2)}.{m.group(3)}"
    return s


def _title_book(book: str) -> str:
    b = book.strip().lower()
    mapping = {
        "john": "John",
        "1john": "1John",
        "2john": "2John",
        "3john": "3John",
        "lev": "Lev",
        "ezek": "Ezek",
        "jer": "Jer",
        "rom": "Rom",
        "isa": "Isa",
        "ps": "Ps",
        "jeremiah": "Jer",
        "revelation": "Rev",
        "psalm": "Ps",
        "leviticus": "Lev",
        "ezekiel": "Ezek",
        "zechariah": "Zech",
        "hos": "Hos",
        "dan": "Dan",
        "daniel": "Dan",
        "job": "Job",
        "prov": "Prov",
        "proverbs": "Prov",
        "eccl": "Eccl",
        "lam": "Lam",
        "lamentations": "Lam",
        "num": "Num",
        "exod": "Exod",
        "deut": "Deut",
        "1cor": "1Cor",
        "2cor": "2Cor",
        "2corinthians": "2Cor",
        "eph": "Eph",
    }
    return mapping.get(b, book[:1].upper() + book[1:] if book else book)


def _collect_router_verses(router: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for vid in router.get("verse_ids") or []:
        n = normalize_verse_ref(str(vid))
        if n:
            out.append(n)
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        for step in path.get("steps") or []:
            n = normalize_verse_ref(str(step))
            if n and re.search(r"\.\d+\.\d+", n):
                out.append(n)
    seen: set[str] = set()
    deduped: list[str] = []
    for v in out:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


def _collect_ann_verses(ann: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for hit in ann.get("top_k") or ann.get("hits") or []:
        if isinstance(hit, dict):
            vid = normalize_verse_ref(str(hit.get("verse_id") or hit.get("id") or ""))
            if vid:
                rows.append(vid)
    return rows


def _collect_rag_verses(insight: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for row in insight.get("rag_evidence") or []:
        if not isinstance(row, dict):
            continue
        direct = normalize_verse_ref(str(row.get("verse_id") or ""))
        if direct and re.search(r"\.\d+\.\d+", direct):
            rows.append(direct)
        sid = str(row.get("source_id") or "")
        for pat in (
            r"verse:([A-Za-z0-9_.]+)",
            r"logos_ann_lite:verse:([A-Za-z0-9_.]+)",
        ):
            m = re.search(pat, sid)
            if m:
                n = normalize_verse_ref(m.group(1))
                if n:
                    rows.append(n)
        snippet = str(row.get("snippet") or "")
        for step in re.findall(r'"([^"]+)"', snippet):
            n = normalize_verse_ref(step)
            if n and re.search(r"\.\d+\.\d+", n):
                rows.append(n)
    seen: set[str] = set()
    deduped: list[str] = []
    for v in rows:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


def _matches_gold(verse: str, gold_ids: list[str], prefixes: list[str]) -> bool:
    if verse in gold_ids:
        return True
    return any(verse.startswith(p) for p in prefixes)


def _hit_at_k(retrieved: list[str], gold_ids: list[str], prefixes: list[str], k: int) -> bool:
    for r in retrieved[:k]:
        if _matches_gold(r, gold_ids, prefixes):
            return True
    return False


def _match_gold(retrieved: list[str], gold_ids: list[str], prefixes: list[str]) -> list[str]:
    hits: list[str] = []
    for r in retrieved:
        if _matches_gold(r, gold_ids, prefixes) and r not in hits:
            hits.append(r)
    return hits


def _artifact_paths(qid: str) -> dict[str, Path]:
    if qid == "q01":
        return {
            "router": ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json",
            "ann": REPORT_DIR / "ann_query_q01_latest.json",
            "insight": ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json",
        }
    return {
        "router": REPORT_DIR / f"router_{qid}_latest.json",
        "ann": REPORT_DIR / f"ann_query_{qid}_latest.json",
        "insight": REPORT_DIR / f"insight_{qid}_latest.json",
    }


def evaluate_item(item: dict[str, Any], k_values: list[int]) -> dict[str, Any]:
    qid = str(item.get("id") or "")
    paths = _artifact_paths(qid)
    router = _read_json(paths["router"])
    ann = _read_json(paths["ann"])
    insight = _read_json(paths["insight"])

    gold_ids = [normalize_verse_ref(str(x)) for x in (item.get("gold_verse_ids") or [])]
    prefixes = [str(x) for x in (item.get("gold_verse_prefixes") or [])]

    router_verses = _collect_router_verses(router)
    ann_verses = _collect_ann_verses(ann)
    rag_verses = _collect_rag_verses(insight)

    router_hits = _match_gold(router_verses, gold_ids, prefixes)
    ann_hits = _match_gold(ann_verses, gold_ids, prefixes)
    rag_hits = _match_gold(rag_verses, gold_ids, prefixes)

    path_hits = 0
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps = [normalize_verse_ref(str(s)) for s in (path.get("steps") or [])]
        if _match_gold(steps, gold_ids, prefixes):
            path_hits += 1

    hit_at_k: dict[str, dict[str, bool]] = {}
    for k in k_values:
        hit_at_k[str(k)] = {
            "router": _hit_at_k(router_verses, gold_ids, prefixes, k),
            "ann": _hit_at_k(ann_verses, gold_ids, prefixes, k),
            "rag": _hit_at_k(rag_verses, gold_ids, prefixes, k),
        }

    gate = item.get("gate") or {}
    tier = str(item.get("eval_tier") or "observational")
    gate_pass = True
    gate_reasons: list[str] = []
    if tier == "gold_required" and gate:
        if path_hits < int(gate.get("router_path_hit_min") or 0):
            gate_pass = False
            gate_reasons.append("router_path_hit_below_min")
        if len(router_hits) < int(gate.get("router_verse_hit_min") or 0):
            gate_pass = False
            gate_reasons.append("router_verse_hit_below_min")
        ann_min = int(gate.get("ann_top8_hit_min") or 0)
        if ann_min > 0 and len(ann_hits) < ann_min:
            gate_pass = False
            gate_reasons.append("ann_hit_below_min")

    return {
        "id": qid,
        "query_ko": item.get("query_ko"),
        "eval_tier": tier,
        "artifacts": {k: str(v) for k, v in paths.items()},
        "artifacts_present": {k: v.is_file() for k, v in paths.items()},
        "router": {
            "bridges_matched": router.get("bridges_matched"),
            "path_count": len(router.get("paths") or []),
            "path_gold_hits": path_hits,
            "verse_count": len(router_verses),
            "gold_hits": router_hits[:12],
            "top_verses": router_verses[:12],
        },
        "ann_lite": {
            "present": paths["ann"].is_file(),
            "gold_hits": ann_hits[:12],
            "top_verses": ann_verses[:8],
            "quality_warn": tier == "gold_required" and len(ann_hits) == 0 and paths["ann"].is_file(),
            "typology_boost_applied": bool((ann.get("typology_boost") or {}).get("applied")),
            "typology_themes": list((ann.get("typology_boost") or {}).get("themes_matched") or []),
        },
        "rag_fusion": {
            "rag_count": len(insight.get("rag_evidence") or []),
            "gold_hits": rag_hits[:12],
        },
        "hit_at_k": hit_at_k,
        "gate_pass": gate_pass if tier == "gold_required" else None,
        "gate_reasons": gate_reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if any gold_required gate fails")
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json

    gold_doc = _read_json(gold_path)
    if gold_doc.get("schema") != "logos_gold_query_eval_v1":
        print(f"[ERROR] invalid gold schema: {gold_path}", file=sys.stderr)
        return 2

    k_values = [int(x) for x in (gold_doc.get("k_at") or [1, 3, 8])]
    items_in = [x for x in (gold_doc.get("items") or []) if isinstance(x, dict)]
    rows = [evaluate_item(it, k_values) for it in items_in]

    required = [r for r in rows if r.get("eval_tier") == "gold_required"]
    all_required_pass = all(r.get("gate_pass") for r in required)
    ann_warns = sum(1 for r in rows if (r.get("ann_lite") or {}).get("quality_warn"))
    typology_boost_count = sum(1 for r in rows if (r.get("ann_lite") or {}).get("typology_boost_applied"))

    doc = {
        "schema": "logos_gold_query_eval_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lane": "logos_magic_orb_quality_cpu",
        "gpu_used": False,
        "nemotron_paths_touched": False,
        "gold_fixture": str(gold_path.relative_to(ROOT)) if gold_path.is_relative_to(ROOT) else str(gold_path),
        "summary": {
            "items_evaluated": len(rows),
            "gold_required_count": len(required),
            "gold_required_all_pass": all_required_pass,
            "ann_quality_warn_count": ann_warns,
            "ann_typology_boost_applied_count": typology_boost_count,
            "corpus_edges_hint": (
                _read_json(ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json").get(
                    "corpus_stats", {}
                ).get("edges_line_count")
                or _read_json(ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json").get(
                    "stats", {}
                ).get("edges_line_count")
            ),
        },
        "rows": rows,
        "recommended_next_ko": [
            "ann_quality_warn>0 → typology lexicon boost (Run-LogosAnnTypologyBoostBatch_v1.ps1) 또는 LoRA rerank",
            "gold_required fail → concept bridge / router theme lane 보강",
            "Track A·실매매 자동 합선 금지",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    print(
        json.dumps(
            {
                "ok": True,
                "gold_required_all_pass": all_required_pass,
                "ann_quality_warn_count": ann_warns,
            },
            ensure_ascii=False,
        )
    )

    if args.strict and not all_required_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
