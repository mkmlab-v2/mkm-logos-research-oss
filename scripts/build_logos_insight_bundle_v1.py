#!/usr/bin/env python3
"""Assemble Logos observational insight_bundle v1 from upstream B-track artifacts.

No doctrinal labels. Outputs JSON matching docs/final/schemas/logos_insight_bundle_v1.schema.json.

citation_pack: populated only from insight candidates and bridge edges that carry a non-empty
snippet (see _SNIPPET_KEYS). If quote_hash is present on the row, it must match sha256(utf-8)
of the whitespace-normalized snippet (optional "sha256:" prefix); mismatches are dropped.
Deduped by final quote_hash; order candidates first, then bridge rows, up to --citation-pack-limit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_NAME = "build_logos_insight_bundle_v1.py"
SCRIPT_VERSION = "1.0.1"
RULESET_ID = "logos_insight_bundle_rules_v0"
RULESET_VERSION = "0.2.0"
MAX_CITATION_SNIPPET_LEN = 8000
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_insight_bundle_v1_latest.json"
DEFAULT_MORPH = ROOT / "docs" / "final" / "artifacts" / "logos_morphology_registry_v1_latest.json"
DEFAULT_SEM = ROOT / "docs" / "final" / "artifacts" / "aramaic_semantic_edge_quality_latest.json"
DEFAULT_INSIGHT = ROOT / "docs" / "final" / "artifacts" / "bible_meaning_insight_candidates_latest.json"
DEFAULT_BRIDGE = ROOT / "docs" / "final" / "artifacts" / "aramaic_cross_corpus_bridge_edges_v1.jsonl"
DEFAULT_REGIME = ROOT / "docs" / "final" / "artifacts" / "aramaic_regime_shift_score_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix_under_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return doc if isinstance(doc, dict) else None


def _load_jsonl_dicts(path: Path, *, limit: int = 500_000) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.is_file():
        return out
    n = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if n >= limit:
            break
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
            n += 1
    return out


_SNIPPET_KEYS = ("snippet", "evidence_snippet", "verbatim_snippet", "quote_snippet", "text_span")
_VERSE_KEYS = ("verse_id", "verse_ref", "source_verse_id")


def _strip_sha256_prefix(h: str) -> str:
    h = h.strip()
    if h.lower().startswith("sha256:"):
        return h[7:].strip()
    return h


def _prepare_snippet(raw: str) -> str:
    """Normalize whitespace for display + hash (schema max length)."""
    norm = " ".join(raw.strip().split())
    if len(norm) > MAX_CITATION_SNIPPET_LEN:
        norm = norm[: MAX_CITATION_SNIPPET_LEN - 3] + "..."
    return norm


def _verbatim_quote_hash(prepared_snippet: str) -> str:
    body = hashlib.sha256(prepared_snippet.encode("utf-8")).hexdigest()
    return f"sha256:{body}"


def _snippet_and_verse_from_row(row: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Return (raw_snippet_or_none, declared_quote_hash_or_none, verse_id_or_none)."""
    snippet: str | None = None
    for k in _SNIPPET_KEYS:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            snippet = v
            break
    qh_raw = row.get("quote_hash")
    declared = qh_raw.strip() if isinstance(qh_raw, str) and qh_raw.strip() else None
    verse_id: str | None = None
    for k in _VERSE_KEYS:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            verse_id = v.strip()[:256]
            break
    return snippet, declared, verse_id


def _maybe_citation_from_row(
    row: dict[str, Any],
    *,
    default_source_track: str | None,
) -> dict[str, Any] | None:
    """One citation_pack item if snippet is non-empty and quote_hash matches (or absent)."""
    raw_snippet, declared_hash, verse_id = _snippet_and_verse_from_row(row)
    if not raw_snippet:
        return None
    prepared = _prepare_snippet(raw_snippet)
    if not prepared:
        return None
    computed = _verbatim_quote_hash(prepared)
    if declared_hash is not None:
        if _strip_sha256_prefix(declared_hash).lower() != _strip_sha256_prefix(computed).lower():
            return None
    st = row.get("source_track")
    source_track = st.strip() if isinstance(st, str) and st.strip() else default_source_track
    if source_track is not None:
        source_track = source_track[:32]
    return {
        "verse_id": verse_id,
        "quote_hash": computed,
        "snippet": prepared,
        "source_track": source_track,
    }


def _build_citation_pack(
    *,
    ins_doc: dict[str, Any] | None,
    bridge_edges: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Only rows with non-empty snippet; quote_hash must match SHA256 of prepared snippet if present."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    if limit <= 0:
        return out

    def push(item: dict[str, Any]) -> None:
        h = item.get("quote_hash")
        if not isinstance(h, str) or h in seen:
            return
        seen.add(h)
        out.append(item)

    if ins_doc:
        cands = ins_doc.get("candidates")
        if isinstance(cands, list):
            for c in cands:
                if len(out) >= limit:
                    return out
                if not isinstance(c, dict):
                    continue
                item = _maybe_citation_from_row(c, default_source_track="B")
                if item:
                    push(item)

    for e in bridge_edges:
        if len(out) >= limit:
            break
        if not isinstance(e, dict):
            continue
        item = _maybe_citation_from_row(e, default_source_track=None)
        if item:
            push(item)

    return out


def _digest_edge(edge: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "src": str(edge.get("src_node_id", "")),
            "dst": str(edge.get("dst_node_id", "")),
            "t": str(edge.get("edge_type", "")),
            "w": str(edge.get("weight", "")),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _summarize_morphology(doc: dict[str, Any]) -> dict[str, Any]:
    layer = doc.get("morphology_layer") if isinstance(doc.get("morphology_layer"), dict) else {}
    return {
        "registry_id": str(layer.get("registry_id", "")),
        "hebrew_atoms_total": int(layer.get("hebrew_atoms_total") or 0),
        "matched_hebrew_atoms": int(layer.get("matched_hebrew_atoms") or 0),
        "unmatched_hebrew_atoms": int(layer.get("unmatched_hebrew_atoms") or 0),
        "coverage_ratio_0_1": float(layer.get("coverage_ratio_0_1") or 0.0),
        "sampled_matched_rows": int(layer.get("sampled_matched_rows") or 0),
        "sampled_scanned_lines": int(layer.get("sampled_scanned_lines") or 0),
    }


def _summarize_semantic_quality(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": str(doc.get("schema", "")),
        "edge_count": int(doc.get("edge_count") or 0),
        "semantic_overlap_mean": float(doc.get("semantic_overlap_mean") or 0.0),
        "shared_token_mean": float(doc.get("shared_token_mean") or 0.0),
        "edge_type_histogram": dict(doc.get("edge_type_histogram") or {})
        if isinstance(doc.get("edge_type_histogram"), dict)
        else {},
    }


def _summarize_insight_candidates(doc: dict[str, Any], *, top_k: int) -> dict[str, Any]:
    cands = doc.get("candidates") if isinstance(doc.get("candidates"), list) else []
    rows: list[dict[str, Any]] = []
    for i, c in enumerate(cands[:top_k]):
        if not isinstance(c, dict):
            continue
        rows.append(
            {
                "rank": i + 1,
                "candidate_id": str(c.get("candidate_id", "")),
                "source_node_id": str(c.get("source_node_id", "")),
                "hub_score": float(c.get("hub_score") or 0.0),
                "path_score": float(c.get("path_score") or 0.0),
                "cluster_size": int(c.get("cluster_size") or 0),
                "regime_tag": str(c.get("regime_tag", "")),
            }
        )
    return {"candidate_count": len(cands), "top_k": top_k, "top": rows}


def _summarize_bridge_edges(edges: list[dict[str, Any]]) -> dict[str, Any]:
    hist: dict[str, int] = {}
    for e in edges:
        t = str(e.get("edge_type", "unknown"))
        hist[t] = hist.get(t, 0) + 1
    return {"edge_count": len(edges), "edge_type_histogram": hist}


def _summarize_regime_shift(doc: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema",
        "generated_at_utc",
        "score_label",
        "shadow_score_0_1",
        "cross_lens_single_trigger_blocked",
    )
    return {k: doc.get(k) for k in keys if k in doc}


def _build_tensions(
    *,
    sem: dict[str, Any] | None,
    bridge_edges: list[dict[str, Any]],
    insight_digest: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    tensions: list[dict[str, Any]] = []
    bridge_n = len(bridge_edges)
    cand_n: int | None
    if isinstance(insight_digest, dict):
        cand_n = int(insight_digest.get("candidate_count") or 0)
    else:
        cand_n = None
    overlap = float((sem or {}).get("semantic_overlap_mean") or 0.0)
    edge_count = int((sem or {}).get("edge_count") or 0)

    if bridge_n > 0 and cand_n == 0 and isinstance(insight_digest, dict):
        e0 = bridge_edges[0]
        tensions.append(
            {
                "tension_axis_id": "bridge_edges_present_insight_candidates_absent_v0",
                "description_neutral": (
                    "Cross-corpus bridge edges exist while insight-candidate extractor "
                    "returned zero candidates in the digest window (observational)."
                ),
                "confidence_0_1": 0.55,
                "evidence_refs": [
                    {
                        "verse_id": None,
                        "quote_hash": _digest_edge(e0),
                        "edge_type": str(e0.get("edge_type") or "unknown"),
                        "source_track": str(e0.get("source_track") or "B"),
                    }
                ],
                "supporting_metrics": {"bridge_edge_count": bridge_n, "insight_candidate_count": cand_n},
                "counter_evidence_refs": [],
            }
        )

    if sem is not None and edge_count > 0 and overlap < 0.5 and bridge_n > 0:
        e0 = bridge_edges[0]
        tensions.append(
            {
                "tension_axis_id": "semantic_overlap_below_half_with_bridge_v0",
                "description_neutral": (
                    "Mean semantic overlap across scored edges is below 0.5 while bridge "
                    "edges are present (observational; not a textual claim)."
                ),
                "confidence_0_1": round(min(0.9, 0.35 + (0.5 - overlap)), 3),
                "evidence_refs": [
                    {
                        "verse_id": None,
                        "quote_hash": _digest_edge(e0),
                        "edge_type": str(e0.get("edge_type") or "unknown"),
                        "source_track": str(e0.get("source_track") or "B"),
                    }
                ],
                "supporting_metrics": {
                    "semantic_overlap_mean": overlap,
                    "semantic_edge_count": edge_count,
                    "bridge_edge_count": bridge_n,
                },
                "counter_evidence_refs": [],
            }
        )

    return tensions


def _audit_inputs_hash(parts: list[tuple[str, str | None]]) -> str:
    lines = [f"{p}\t{h or ''}" for p, h in sorted(parts)]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def build_bundle(
    *,
    morphology_path: Path,
    semantic_path: Path,
    insight_path: Path,
    bridge_path: Path,
    regime_path: Path,
    top_k: int,
    citation_pack_limit: int,
) -> dict[str, Any]:
    missing: list[str] = []
    upstream: list[dict[str, Any]] = []
    parts: list[tuple[str, str | None]] = []

    for label, path in (
        ("morphology_registry", morphology_path),
        ("semantic_edge_quality", semantic_path),
        ("insight_candidates", insight_path),
        ("cross_corpus_bridge", bridge_path),
        ("regime_shift_shadow", regime_path),
    ):
        rel = _posix_under_root(path)
        h = _file_sha256(path)
        upstream.append({"path": rel, "sha256": h})
        parts.append((rel, h))
        if h is None:
            missing.append(label)

    morph_doc = _read_json(morphology_path)
    sem_doc = _read_json(semantic_path)
    ins_doc = _read_json(insight_path)
    regime_doc = _read_json(regime_path)
    bridge_edges = _load_jsonl_dicts(bridge_path)

    aggregation: dict[str, Any] = {}
    if morph_doc:
        aggregation["morphology_summary"] = _summarize_morphology(morph_doc)
    if sem_doc:
        aggregation["semantic_edge_quality_digest"] = _summarize_semantic_quality(sem_doc)
    if ins_doc:
        aggregation["insight_candidates_digest"] = _summarize_insight_candidates(ins_doc, top_k=top_k)
    if bridge_edges:
        aggregation["cross_corpus_bridge_summary"] = _summarize_bridge_edges(bridge_edges)
    if regime_doc:
        aggregation["regime_shift_shadow"] = _summarize_regime_shift(regime_doc)

    insight_digest = aggregation.get("insight_candidates_digest")
    if not isinstance(insight_digest, dict):
        insight_digest = None

    tensions = _build_tensions(sem=sem_doc, bridge_edges=bridge_edges, insight_digest=insight_digest)

    citation_pack = _build_citation_pack(
        ins_doc=ins_doc,
        bridge_edges=bridge_edges,
        limit=max(0, min(256, int(citation_pack_limit))),
    )

    degraded = len(missing) > 0

    unknown_frac = min(
        1.0,
        (len(missing) / 5.0)
        + (0.15 if not tensions else 0.0)
        + (0.1 if not citation_pack else 0.0),
    )
    band = "high" if unknown_frac >= 0.6 else ("mid" if unknown_frac >= 0.25 else "low")

    fp_src = json.dumps(
        {
            "missing": sorted(missing),
            "upstream_sha": [u.get("sha256") for u in upstream],
            "citation_hashes": sorted(str(c.get("quote_hash", "")) for c in citation_pack),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    query_fp = "sha256:" + hashlib.sha256(fp_src.encode("utf-8")).hexdigest()

    return {
        "schema": "logos_insight_bundle_v1",
        "schema_version": "1.0.0",
        "generated_at_utc": _now_utc(),
        "generator": {"script": SCRIPT_NAME, "version": SCRIPT_VERSION},
        "policy": {"research_only": True, "non_gating": True, "no_doctrinal_labels": True},
        "hypothesis_tier": "[HYPO]",
        "upstream_artifacts": upstream,
        "degraded": degraded,
        "missing_upstream": missing,
        "query": {
            "query_fingerprint": query_fp,
            "scope": None,
            "corpus_revision": None,
        },
        "aggregation": aggregation,
        "tension_hypotheses": tensions,
        "citation_pack": citation_pack,
        "audit": {
            "inputs_hash": "sha256:" + _audit_inputs_hash(parts),
            "ruleset_id": RULESET_ID,
            "ruleset_version": RULESET_VERSION,
            "determinism_note": (
                f"bundle_v1 rules={RULESET_ID}@{RULESET_VERSION}; "
                "tension rules: bridge_vs_insight_gap, overlap<0.5 with bridge; "
                "citation_pack: only rows with non-empty snippet (keys "
                f"{', '.join(_SNIPPET_KEYS)}); quote_hash must equal "
                "sha256(utf-8) of whitespace-normalized snippet (prefix sha256: optional) "
                "when quote_hash is set; else hash is computed; dedupe by quote_hash."
            ),
        },
        "uncertainty": {"uncertainty_band": band, "unknown_fraction_0_1": round(unknown_frac, 4)},
        "gating": {"pastoral_and_trading": "non_gating"},
        "human_review_hint": (
            "Observational metrics only; pastoral or trading decisions are out of scope."
        ),
        "llm_injection_whitelist": [
            "policy",
            "hypothesis_tier",
            "aggregation",
            "tension_hypotheses",
            "citation_pack",
            "uncertainty",
            "gating",
            "missing_upstream",
            "degraded",
        ],
        "forbidden_patterns_ref": "scripts/logos_response_validator_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--morphology-json", type=Path, default=DEFAULT_MORPH)
    ap.add_argument("--semantic-quality-json", type=Path, default=DEFAULT_SEM)
    ap.add_argument("--insight-candidates-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--bridge-edges-jsonl", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--regime-shift-json", type=Path, default=DEFAULT_REGIME)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument(
        "--citation-pack-limit",
        type=int,
        default=16,
        help="Max citation_pack items (non-empty snippet; declared quote_hash must match when set; 0 disables)",
    )
    args = ap.parse_args()

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    morph = args.morphology_json if args.morphology_json.is_absolute() else ROOT / args.morphology_json
    sem = args.semantic_quality_json if args.semantic_quality_json.is_absolute() else ROOT / args.semantic_quality_json
    ins = args.insight_candidates_json if args.insight_candidates_json.is_absolute() else ROOT / args.insight_candidates_json
    bridge = args.bridge_edges_jsonl if args.bridge_edges_jsonl.is_absolute() else ROOT / args.bridge_edges_jsonl
    regime = args.regime_shift_json if args.regime_shift_json.is_absolute() else ROOT / args.regime_shift_json

    bundle = build_bundle(
        morphology_path=morph,
        semantic_path=sem,
        insight_path=ins,
        bridge_path=bridge,
        regime_path=regime,
        top_k=max(1, min(32, int(args.top_k))),
        citation_pack_limit=int(args.citation_pack_limit),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "degraded": bundle["degraded"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
