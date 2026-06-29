#!/usr/bin/env python3
"""PersonaDiary → Logos sidebar smoke v1 [HYPO].

Loads one PersonaDiary B-track export, selects up to 3 NON_GATING Logos hits from
existing pilot artifacts (philosophy ann_lite, GraphRAG router, concept bridge registry).
No new embedding/LLM/graph ingest. No prophecy vote or Track A fields.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_ID = "personadiary_logos_sidebar_smoke_v1"
VERSION = "1.1.0"
DEFAULT_OUT = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json"
REPORTS_OUT = ROOT / "reports/personadiary_logos_sidebar_smoke_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/personadiary_logos_sidebar_smoke_v1.schema.json"

DEFAULT_EXPORT = (
    ROOT / "reports/constitution/btrack_pilot/personadiary_export_inbox/fixture_sample_export.json"
)
DEFAULT_PHILOSOPHY = ROOT / "docs/final/artifacts/philosophy_lane_rag_pilot_v1_latest.json"
DEFAULT_GRAPHRAG = ROOT / "docs/final/artifacts/graphrag_pilot_router_latest.json"
DEFAULT_LOGOS_REGISTRY = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
DEFAULT_FORBIDDEN = ROOT / "docs/final/artifacts/schemas/philosophy_lane_rag_pilot_forbidden_substrings_v1.json"

MAX_HITS = 3
VERSE_RE = re.compile(r"verse_id='([^']+)'")
SCORE_RE = re.compile(r"score=([\d.]+)")
TOKEN_RE = re.compile(r"[가-힣]{2,}|[a-zA-Z]{3,}")


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


def _pointer(path: Path) -> dict[str, Any]:
    return {"path": _rel(path), "present": path.is_file()}


def _collect_diary_text(export: dict[str, Any]) -> str:
    parts: list[str] = []
    payload = export.get("payload") or {}
    ns = (payload.get("north_star_by_lane_hypo_v1") or {}).get("lanes") or {}
    if isinstance(ns, dict):
        for lane in ns.values():
            if isinstance(lane, dict):
                line = str(lane.get("one_line") or "").strip()
                if line:
                    parts.append(line)
    for item in payload.get("weekly_top5") or []:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                parts.append(text)
    noa = payload.get("next_one_action") or {}
    if isinstance(noa, dict):
        text = str(noa.get("text") or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text)}


def _parse_ann_lite_block(block: dict[str, Any]) -> tuple[str | None, float | None]:
    summary = str(block.get("summary") or "")
    vm = VERSE_RE.search(summary)
    sm = SCORE_RE.search(summary)
    verse_id = vm.group(1) if vm else None
    score = float(sm.group(1)) if sm else None
    return verse_id, score


def _ann_lite_hits(philosophy: dict[str, Any], diary_tokens: set[str]) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    seen_verse: set[str] = set()
    for block in philosophy.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        if str(block.get("source_rail") or "") != "logos_ann_lite":
            continue
        verse_id, ann_score = _parse_ann_lite_block(block)
        if not verse_id or verse_id in seen_verse:
            continue
        summary = str(block.get("summary") or "")
        block_tokens = _tokenize(summary + " " + str(block.get("detail") or ""))
        overlap = len(diary_tokens & block_tokens)
        base = ann_score if ann_score is not None else 0.0
        score = base + overlap * 0.05
        hit = {
            "hit_type": "logos_ann_lite",
            "source_rail": "logos_ann_lite",
            "verse_id": verse_id,
            "score": round(score, 6),
            "summary": summary[:500],
            "match_reason": f"ann_lite_score+token_overlap={overlap}",
        }
        scored.append((score, hit))
        seen_verse.add(verse_id)
    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored]


def _graphrag_motif_hits(graphrag: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = graphrag.get("selected_nodes") or []
    if not isinstance(nodes, list):
        return []
    ranked: list[tuple[float, dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        path_score = float(node.get("path_score") or 0.0)
        hub_score = float(node.get("hub_score") or 0.0)
        score = path_score + hub_score * 0.1
        ranked.append(
            (
                score,
                {
                    "hit_type": "graphrag_motif",
                    "source_rail": "graphrag_pilot_router",
                    "node_id": str(node.get("node_id") or ""),
                    "assigned_symbol": str(node.get("assigned_symbol") or ""),
                    "score": round(score, 6),
                    "summary": (
                        f"graphrag motif symbol={node.get('assigned_symbol')} "
                        f"node_id={node.get('node_id')}"
                    )[:500],
                    "match_reason": "graphrag_selected_node_rank",
                },
            )
        )
    ranked.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    seen_symbol: set[str] = set()
    for _, hit in ranked:
        sym = hit.get("assigned_symbol") or ""
        if sym in seen_symbol:
            continue
        seen_symbol.add(sym)
        out.append(hit)
    return out


def _concept_bridge_candidates(registry: dict[str, Any]) -> list[dict[str, Any]]:
    entries = registry.get("entries") or []
    if not isinstance(entries, list):
        return []
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        label = str(entry.get("label_ko") or "")
        concept_id = str(entry.get("concept_id") or "")
        out.append(
            {
                "hit_type": "concept_bridge",
                "source_rail": "logos_concept_bridge_registry",
                "concept_id": concept_id,
                "label_ko": label,
                "summary": f"concept_bridge {concept_id} label_ko={label}"[:500],
            }
        )
    return out


def _concept_bridge_hit(registry: dict[str, Any], diary_text: str) -> dict[str, Any] | None:
    scored = _score_concept_bridges(_concept_bridge_candidates(registry), diary_text)
    return scored[0] if scored else None


def _score_concept_bridges(
    candidates: list[dict[str, Any]], diary_text: str
) -> list[dict[str, Any]]:
    diary_lower = diary_text.lower()
    diary_tokens = _tokenize(diary_text)
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in candidates:
        label = str(candidate.get("label_ko") or "")
        concept_id = str(candidate.get("concept_id") or "")
        hay = f"{label} {concept_id}".lower()
        overlap = sum(1 for tok in diary_tokens if tok in hay)
        if "쉼" in diary_text and "turmoil" in concept_id:
            overlap += 2
        if "마음" in diary_text and ("mercy" in concept_id or "compassion" in concept_id):
            overlap += 1
        if overlap <= 0:
            continue
        hit = {
            **candidate,
            "score": float(overlap),
            "match_reason": f"diary_token_overlap={overlap}",
        }
        scored.append((float(overlap), hit))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored]


def _build_candidate_pools(
    philosophy: dict[str, Any],
    graphrag: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    ann_pool: list[dict[str, Any]] = []
    seen_verse: set[str] = set()
    for block in philosophy.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        if str(block.get("source_rail") or "") != "logos_ann_lite":
            continue
        verse_id, ann_score = _parse_ann_lite_block(block)
        if not verse_id or verse_id in seen_verse:
            continue
        summary = str(block.get("summary") or "")
        ann_pool.append(
            {
                "hit_type": "logos_ann_lite",
                "source_rail": "logos_ann_lite",
                "verse_id": verse_id,
                "ann_score": ann_score,
                "summary": summary[:500],
                "detail": str(block.get("detail") or "")[:8000],
            }
        )
        seen_verse.add(verse_id)
    ann_pool.sort(key=lambda x: float(x.get("ann_score") or 0.0), reverse=True)

    motif_pool: list[dict[str, Any]] = []
    for hit in _graphrag_motif_hits(graphrag):
        motif_pool.append(
            {
                "hit_type": "graphrag_motif",
                "source_rail": "graphrag_pilot_router",
                "node_id": hit.get("node_id"),
                "assigned_symbol": hit.get("assigned_symbol"),
                "path_score": hit.get("score"),
                "summary": hit.get("summary"),
            }
        )

    return {
        "logos_ann_lite": ann_pool,
        "graphrag_motif": motif_pool,
        "concept_bridge": _concept_bridge_candidates(registry),
    }


def _assemble_hits(
    ann_hits: list[dict[str, Any]],
    motif_hits: list[dict[str, Any]],
    bridge_hit: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    if ann_hits:
        combined.append(ann_hits[0])
    if motif_hits:
        combined.append(motif_hits[0])
    if bridge_hit:
        combined.append(bridge_hit)
    for hit in ann_hits[1:] + motif_hits[1:]:
        if len(combined) >= MAX_HITS:
            break
        key = hit.get("verse_id") or hit.get("node_id") or hit.get("concept_id")
        existing = {
            h.get("verse_id") or h.get("node_id") or h.get("concept_id") for h in combined
        }
        if key not in existing:
            combined.append(hit)
    while len(combined) < MAX_HITS:
        pool = ann_hits + motif_hits
        if bridge_hit:
            pool.append(bridge_hit)
        added = False
        for hit in pool:
            key = hit.get("verse_id") or hit.get("node_id") or hit.get("concept_id")
            existing = {
                h.get("verse_id") or h.get("node_id") or h.get("concept_id") for h in combined
            }
            if key not in existing:
                combined.append(hit)
                added = True
                if len(combined) >= MAX_HITS:
                    break
        if not added:
            break
    for i, hit in enumerate(combined[:MAX_HITS], start=1):
        hit["rank"] = i
    return combined[:MAX_HITS]


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


def build_sidebar(
    *,
    export_path: Path,
    philosophy_path: Path,
    graphrag_path: Path,
    logos_registry_path: Path,
    forbidden_path: Path,
) -> dict[str, Any]:
    export = _read_json(export_path)
    philosophy = _read_json(philosophy_path)
    graphrag = _read_json(graphrag_path)
    registry = _read_json(logos_registry_path)

    diary_text = _collect_diary_text(export)
    diary_tokens = _tokenize(diary_text)

    ann_hits = _ann_lite_hits(philosophy, diary_tokens)
    motif_hits = _graphrag_motif_hits(graphrag)
    bridge_hit = _concept_bridge_hit(registry, diary_text)
    hits = _assemble_hits(ann_hits, motif_hits, bridge_hit)
    candidate_pools = _build_candidate_pools(philosophy, graphrag, registry)

    serialized = json.dumps(hits, ensure_ascii=False)
    forbidden_violations = _forbidden_scan(serialized + diary_text, forbidden_path)

    required_ok = all(
        p.is_file() for p in (export_path, philosophy_path, graphrag_path, logos_registry_path, forbidden_path)
    )
    sidebar_generation_ok = required_ok and len(hits) == MAX_HITS and len(forbidden_violations) == 0

    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "lane_id": "personadiary_logos_sidebar",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "decision_authority": "human_only",
        "prophecy_vote": "none",
        "policy": {
            "non_gating": True,
            "opt_in_only": True,
            "forbidden_config": _rel(forbidden_path),
        },
        "input_export": {
            "path": _rel(export_path),
            "pseudonym_id": str(export.get("pseudonym_id") or ""),
            "diary_text_chars": len(diary_text),
        },
        "sidebar_generation_ok": sidebar_generation_ok,
        "hits": hits,
        "candidate_pools": candidate_pools,
        "rerank_contract": {
            "client_local_diary": True,
            "max_hits": MAX_HITS,
            "prophecy_vote": "none",
        },
        "forbidden_violations": forbidden_violations,
        "upstream_pointers": {
            "philosophy_lane_rag_pilot": _pointer(philosophy_path),
            "graphrag_pilot_router": _pointer(graphrag_path),
            "logos_concept_bridge_registry": _pointer(logos_registry_path),
        },
        "graphrag_question": str(graphrag.get("question") or "")[:200] or None,
        "consumer_contract_ko": (
            "PersonaDiary 일기 1건에 대해 Logos 참조 사이드바 후보 3개를 제시합니다. "
            "NON_GATING·opt-in·prophecy_vote none. Track A·실매매·send_gate 자동 승격 없음. "
            "은유·서사 영감 참고만이며 방향 예측·적중률 주장 금지."
        ),
        "ok": sidebar_generation_ok,
        "headline_ko": [
            f"hits={len(hits)}",
            f"sidebar_generation_ok={sidebar_generation_ok}",
            "prophecy_vote=none",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--export", type=Path, default=DEFAULT_EXPORT)
    ap.add_argument("--philosophy", type=Path, default=DEFAULT_PHILOSOPHY)
    ap.add_argument("--graphrag", type=Path, default=DEFAULT_GRAPHRAG)
    ap.add_argument("--logos-registry", type=Path, default=DEFAULT_LOGOS_REGISTRY)
    ap.add_argument("--forbidden-config", type=Path, default=DEFAULT_FORBIDDEN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reports-output", type=Path, default=REPORTS_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if ok=false")
    ap.add_argument("--skip-public-sync", action="store_true")
    args = ap.parse_args(argv)

    payload = build_sidebar(
        export_path=args.export,
        philosophy_path=args.philosophy,
        graphrag_path=args.graphrag,
        logos_registry_path=args.logos_registry,
        forbidden_path=args.forbidden_config,
    )

    for path in (args.output, args.reports_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.strict and not payload.get("ok"):
        print("FAIL: personadiary_logos_sidebar_smoke not ok", file=sys.stderr)
        return 1

    if not args.skip_public_sync:
        sync = subprocess.run(
            [sys.executable, str(ROOT / "scripts/sync_personadiary_logos_sidebar_public_v1.py")],
            cwd=str(ROOT),
        )
        if sync.returncode != 0:
            return sync.returncode

    print(
        f"OK hits={len(payload.get('hits') or [])} "
        f"sidebar_generation_ok={payload.get('sidebar_generation_ok')} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
