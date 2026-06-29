#!/usr/bin/env python3
"""Read-only manifest: external biblical KG sources → MKM Logos ingest targets [HYPO].

Does not download third-party datasets. Records pointers, license notes, and local
gap mapping for Phase 1 lemma/xref enrichment.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_external_kg_ingest_manifest_v1_latest.json"

SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "gnosis_kg",
        "title": "Gnosis biblical knowledge graph",
        "url": "https://github.com/spearssoftware/gnosis",
        "license_hint": "upstream CC-BY / open-licensed merges — verify SOURCES.md per release",
        "provides": ["strongs", "cross_references", "morphology", "verse_index"],
        "mkm_targets": [
            "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl",
            "data/logos/bible_meaning_graph_*_v1.jsonl",
        ],
        "ingest_mode": "read_only_pointer",
        "ingest_status": "not_run",
    },
    {
        "source_id": "sinew_xref",
        "title": "Sinew sourced Bible connection graph",
        "url": "https://github.com/LucasGalhardoLima/sinew",
        "license_hint": "public-domain text + CC-BY edges — provenance per edge",
        "provides": ["cross_reference_provenance", "canonical_ids", "chapter_vectors"],
        "mkm_targets": [
            "docs/final/artifacts/logos_sinew_xref_edges_v1.jsonl",
            "docs/final/artifacts/bible_meaning_graph_*_v1.jsonl",
            "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json",
        ],
        "ingest_mode": "read_only_pointer",
        "ingest_status": "not_run",
    },
    {
        "source_id": "open_scripture_intelligence",
        "title": "Open Scripture Intelligence",
        "url": "https://github.com/echology-io/open-scripture-intelligence",
        "license_hint": "public-domain translations + structured exports — verify repo LICENSE",
        "provides": ["canonical_jsonl", "xref_graph", "embeddings", "entity_metadata"],
        "mkm_targets": [
            "docs/final/artifacts/logos_osi_xref_edges_v1.jsonl",
            "data/logos/verse_4pipeline_full_31102.json",
            "docs/final/artifacts/logos_corpus_manifest_v1_latest.json",
        ],
        "ingest_mode": "read_only_pointer",
        "ingest_status": "not_run",
    },
    {
        "source_id": "theographic",
        "title": "Theographic Bible knowledge graph",
        "url": "https://theographic.netlify.app/about/",
        "license_hint": "CC-BY 4.0 unless noted",
        "provides": ["people_places_events_graph", "graphql_api"],
        "mkm_targets": [
            "docs/final/artifacts/logos_theographic_entity_edges_v1.jsonl",
            "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl",
        ],
        "ingest_mode": "read_only_pointer",
        "ingest_status": "not_run",
    },
    {
        "source_id": "scriptures_js_gematria",
        "title": "scriptures-js gematria / Strong lookup",
        "url": "https://github.com/metaxiamultimedia/scriptures-js",
        "license_hint": "verify package licenses — primary-source cited gematria methods",
        "provides": ["gematria_methods", "strongs_lookup", "morphology"],
        "mkm_targets": [
            "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl",
            "scripts/core/gematria_to_4d_bridge.py",
            "docs/final/artifacts/logos_cosmic_anchor_batch_v1/",
        ],
        "ingest_mode": "read_only_pointer",
        "ingest_status": "not_run",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _local_snapshot() -> dict[str, Any]:
    lemma_jsonl = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
    lemma_manifest = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
    sinew_jsonl = ROOT / "docs/final/artifacts/logos_sinew_xref_edges_v1.jsonl"
    sinew_manifest = ROOT / "docs/final/artifacts/logos_sinew_xref_edges_v1_latest.json"
    osi_jsonl = ROOT / "docs/final/artifacts/logos_osi_xref_edges_v1.jsonl"
    osi_manifest = ROOT / "docs/final/artifacts/logos_osi_xref_edges_v1_latest.json"
    theographic_jsonl = ROOT / "docs/final/artifacts/logos_theographic_entity_edges_v1.jsonl"
    theographic_manifest = ROOT / "docs/final/artifacts/logos_theographic_entity_edges_v1_latest.json"
    gematria_lexicon_jsonl = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1.jsonl"
    gematria_lexicon_manifest = ROOT / "docs/final/artifacts/logos_scriptures_js_gematria_lexicon_v1_latest.json"
    bridge = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
    router = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"

    lemma_doc: dict[str, Any] = {}
    if lemma_manifest.is_file():
        try:
            raw = json.loads(lemma_manifest.read_text(encoding="utf-8-sig"))
            lemma_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            lemma_doc = {}

    sinew_doc: dict[str, Any] = {}
    if sinew_manifest.is_file():
        try:
            raw = json.loads(sinew_manifest.read_text(encoding="utf-8-sig"))
            sinew_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            sinew_doc = {}

    osi_doc: dict[str, Any] = {}
    if osi_manifest.is_file():
        try:
            raw = json.loads(osi_manifest.read_text(encoding="utf-8-sig"))
            osi_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            osi_doc = {}

    theographic_doc: dict[str, Any] = {}
    if theographic_manifest.is_file():
        try:
            raw = json.loads(theographic_manifest.read_text(encoding="utf-8-sig"))
            theographic_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            theographic_doc = {}

    gematria_lexicon_doc: dict[str, Any] = {}
    if gematria_lexicon_manifest.is_file():
        try:
            raw = json.loads(gematria_lexicon_manifest.read_text(encoding="utf-8-sig"))
            gematria_lexicon_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            gematria_lexicon_doc = {}

    bridge_doc: dict[str, Any] = {}
    if bridge.is_file():
        try:
            raw = json.loads(bridge.read_text(encoding="utf-8-sig"))
            bridge_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            bridge_doc = {}

    router_doc: dict[str, Any] = {}
    if router.is_file():
        try:
            raw = json.loads(router.read_text(encoding="utf-8-sig"))
            router_doc = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            router_doc = {}

    lemma_lines = 0
    if lemma_jsonl.is_file():
        with lemma_jsonl.open("r", encoding="utf-8") as fh:
            lemma_lines = sum(1 for line in fh if line.strip())

    sinew_lines = 0
    if sinew_jsonl.is_file():
        with sinew_jsonl.open("r", encoding="utf-8") as fh:
            sinew_lines = sum(1 for line in fh if line.strip())

    osi_lines = 0
    if osi_jsonl.is_file():
        with osi_jsonl.open("r", encoding="utf-8") as fh:
            osi_lines = sum(1 for line in fh if line.strip())

    theographic_lines = 0
    if theographic_jsonl.is_file():
        with theographic_jsonl.open("r", encoding="utf-8") as fh:
            theographic_lines = sum(1 for line in fh if line.strip())

    gematria_lexicon_lines = 0
    if gematria_lexicon_jsonl.is_file():
        with gematria_lexicon_jsonl.open("r", encoding="utf-8") as fh:
            gematria_lexicon_lines = sum(1 for line in fh if line.strip())

    return {
        "lemma_verse_edges_jsonl_lines": lemma_lines,
        "lemma_manifest_edge_count": int(lemma_doc.get("edge_count") or 0),
        "sinew_xref_edges_jsonl_lines": sinew_lines,
        "sinew_manifest_edge_count": int(sinew_doc.get("edge_count") or 0),
        "osi_xref_edges_jsonl_lines": osi_lines,
        "osi_manifest_edge_count": int(osi_doc.get("edge_count") or 0),
        "theographic_entity_edges_jsonl_lines": theographic_lines,
        "theographic_manifest_edge_count": int(theographic_doc.get("edge_count") or 0),
        "scriptures_js_gematria_lexicon_jsonl_lines": gematria_lexicon_lines,
        "scriptures_js_gematria_lexicon_entry_count": int(
            gematria_lexicon_doc.get("entry_count") or gematria_lexicon_doc.get("edge_count") or 0
        ),
        "lemma_hit_anchors": int((bridge_doc.get("summary") or {}).get("lemma_hit_anchors") or 0),
        "subgraph_router_paths": int((router_doc.get("summary") or {}).get("paths") or len(router_doc.get("paths") or [])),
        "artifacts": {
            "lemma_jsonl": _rel(lemma_jsonl),
            "lemma_manifest": _rel(lemma_manifest),
            "sinew_xref_jsonl": _rel(sinew_jsonl),
            "sinew_xref_manifest": _rel(sinew_manifest),
            "osi_xref_jsonl": _rel(osi_jsonl),
            "osi_xref_manifest": _rel(osi_manifest),
            "theographic_entity_jsonl": _rel(theographic_jsonl),
            "theographic_entity_manifest": _rel(theographic_manifest),
            "scriptures_js_gematria_lexicon_jsonl": _rel(gematria_lexicon_jsonl),
            "scriptures_js_gematria_lexicon_manifest": _rel(gematria_lexicon_manifest),
            "graph_bridge": _rel(bridge),
            "subgraph_router": _rel(router),
        },
    }


def build_manifest() -> dict[str, Any]:
    gnosis_report_path = ROOT / "reports/logos_gnosis_kg_ingest_v1_latest.json"
    gnosis_fetch_path = ROOT / "reports/logos_gnosis_kg_fetch_v1_latest.json"
    gnosis_ingest_status = "not_run"
    gnosis_ingest_edges = 0
    gnosis_release_tag = None
    if gnosis_fetch_path.is_file():
        try:
            fetch = json.loads(gnosis_fetch_path.read_text(encoding="utf-8-sig"))
            if isinstance(fetch, dict):
                gnosis_release_tag = fetch.get("release_tag")
        except json.JSONDecodeError:
            pass
    if gnosis_report_path.is_file():
        try:
            rep = json.loads(gnosis_report_path.read_text(encoding="utf-8-sig"))
            if isinstance(rep, dict) and rep.get("schema") == "logos_gnosis_kg_ingest_v1":
                built = int(rep.get("edges_built") or 0)
                gnosis_ingest_edges = built
                if built <= 0:
                    gnosis_ingest_status = "not_run"
                elif rep.get("license_ack") == "fixture_offline_only":
                    gnosis_ingest_status = "fixture_or_local_ok"
                elif built >= 10000:
                    gnosis_ingest_status = "release_full_ok"
                else:
                    gnosis_ingest_status = "release_partial_ok"
        except json.JSONDecodeError:
            pass

    sinew_report_path = ROOT / "reports/logos_sinew_xref_ingest_v1_latest.json"
    sinew_fetch_path = ROOT / "reports/logos_sinew_xref_fetch_v1_latest.json"
    sinew_ingest_status = "not_run"
    sinew_ingest_edges = 0
    if sinew_report_path.is_file():
        try:
            rep = json.loads(sinew_report_path.read_text(encoding="utf-8-sig"))
            if isinstance(rep, dict) and rep.get("schema") == "logos_sinew_xref_ingest_v1":
                built = int(rep.get("edges_built") or 0)
                sinew_ingest_edges = built
                if built <= 0:
                    sinew_ingest_status = "not_run"
                elif rep.get("license_ack") == "fixture_offline_only":
                    sinew_ingest_status = "fixture_or_local_ok"
                elif built >= 10000:
                    sinew_ingest_status = "release_full_ok"
                else:
                    sinew_ingest_status = "release_partial_ok"
        except json.JSONDecodeError:
            pass

    osi_report_path = ROOT / "reports/logos_osi_xref_ingest_v1_latest.json"
    osi_fetch_path = ROOT / "reports/logos_osi_fetch_v1_latest.json"
    osi_ingest_status = "not_run"
    osi_ingest_edges = 0
    if osi_report_path.is_file():
        try:
            rep = json.loads(osi_report_path.read_text(encoding="utf-8-sig"))
            if isinstance(rep, dict) and rep.get("schema") == "logos_osi_xref_ingest_v1":
                built = int(rep.get("edges_built") or 0)
                osi_ingest_edges = built
                if built <= 0:
                    osi_ingest_status = "not_run"
                elif rep.get("license_ack") == "fixture_offline_only":
                    osi_ingest_status = "fixture_or_local_ok"
                elif built >= 10000:
                    osi_ingest_status = "release_full_ok"
                else:
                    osi_ingest_status = "release_partial_ok"
        except json.JSONDecodeError:
            pass

    theographic_report_path = ROOT / "reports/logos_theographic_entity_ingest_v1_latest.json"
    theographic_fetch_path = ROOT / "reports/logos_theographic_fetch_v1_latest.json"
    theographic_ingest_status = "not_run"
    theographic_ingest_edges = 0
    if theographic_report_path.is_file():
        try:
            rep = json.loads(theographic_report_path.read_text(encoding="utf-8-sig"))
            if isinstance(rep, dict) and rep.get("schema") == "logos_theographic_entity_ingest_v1":
                built = int(rep.get("edges_built") or 0)
                theographic_ingest_edges = built
                if built <= 0:
                    theographic_ingest_status = "not_run"
                elif rep.get("license_ack") == "fixture_offline_only":
                    theographic_ingest_status = "fixture_or_local_ok"
                elif built >= 10000:
                    theographic_ingest_status = "release_full_ok"
                else:
                    theographic_ingest_status = "release_partial_ok"
        except json.JSONDecodeError:
            pass

    scriptures_js_report_path = ROOT / "reports/logos_scriptures_js_gematria_ingest_v1_latest.json"
    scriptures_js_fetch_path = ROOT / "reports/logos_scriptures_js_gematria_fetch_v1_latest.json"
    scriptures_js_ingest_status = "not_run"
    scriptures_js_ingest_entries = 0
    if scriptures_js_report_path.is_file():
        try:
            rep = json.loads(scriptures_js_report_path.read_text(encoding="utf-8-sig"))
            if isinstance(rep, dict) and rep.get("schema") == "logos_scriptures_js_gematria_ingest_v1":
                built = int(
                    rep.get("entries_built") or rep.get("rows_built") or rep.get("edges_built") or 0
                )
                scriptures_js_ingest_entries = built
                if built <= 0:
                    scriptures_js_ingest_status = "not_run"
                elif rep.get("license_ack") in ("fixture_offline_only", "verify_upstream_fixture"):
                    scriptures_js_ingest_status = "fixture_or_local_ok"
                elif built >= 1000:
                    scriptures_js_ingest_status = "release_full_ok"
                else:
                    scriptures_js_ingest_status = "release_partial_ok"
        except json.JSONDecodeError:
            pass

    sources = []
    for row in SOURCES:
        item = dict(row)
        if item.get("source_id") == "gnosis_kg":
            item["ingest_status"] = gnosis_ingest_status
            item["last_ingest_edges_built"] = gnosis_ingest_edges
            item["release_tag"] = gnosis_release_tag
            item["ingest_report"] = _rel(gnosis_report_path) if gnosis_report_path.is_file() else None
            item["fetch_report"] = _rel(gnosis_fetch_path) if gnosis_fetch_path.is_file() else None
        elif item.get("source_id") == "sinew_xref":
            item["ingest_status"] = sinew_ingest_status
            item["last_ingest_edges_built"] = sinew_ingest_edges
            item["ingest_report"] = _rel(sinew_report_path) if sinew_report_path.is_file() else None
            item["fetch_report"] = _rel(sinew_fetch_path) if sinew_fetch_path.is_file() else None
        elif item.get("source_id") == "open_scripture_intelligence":
            item["ingest_status"] = osi_ingest_status
            item["last_ingest_edges_built"] = osi_ingest_edges
            item["ingest_report"] = _rel(osi_report_path) if osi_report_path.is_file() else None
            item["fetch_report"] = _rel(osi_fetch_path) if osi_fetch_path.is_file() else None
        elif item.get("source_id") == "theographic":
            item["ingest_status"] = theographic_ingest_status
            item["last_ingest_edges_built"] = theographic_ingest_edges
            item["ingest_report"] = _rel(theographic_report_path) if theographic_report_path.is_file() else None
            item["fetch_report"] = _rel(theographic_fetch_path) if theographic_fetch_path.is_file() else None
        elif item.get("source_id") == "scriptures_js_gematria":
            item["ingest_status"] = scriptures_js_ingest_status
            item["last_ingest_entries_built"] = scriptures_js_ingest_entries
            item["ingest_report"] = (
                _rel(scriptures_js_report_path) if scriptures_js_report_path.is_file() else None
            )
            item["fetch_report"] = (
                _rel(scriptures_js_fetch_path) if scriptures_js_fetch_path.is_file() else None
            )
        sources.append(item)

    return {
        "schema": "logos_external_kg_ingest_manifest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "non_gating": True,
        "purpose": (
            "Pointer manifest for external biblical KG / gematria lexicon sources. "
            "No automatic ingest or Track A promotion."
        ),
        "operational_4d_ssot": "gematria_bridge_v1 S-L-K-M",
        "forbidden_core_renames": ["taeyang", "taeeum", "soyang", "soeum_as_slkm_axes"],
        "external_sources": sources,
        "local_snapshot": _local_snapshot(),
        "reproduce": "py scripts/build_logos_external_kg_ingest_manifest_v1.py",
        "next_ingest_chain": (
            "py scripts/run_logos_scriptures_js_gematria_ingest_chain_v1.py "
            "--scriptures-js-dir storage/external_kg/scriptures_js_v1 --ack-license-verify-upstream --skip-download"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_manifest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    snap = doc["local_snapshot"]
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "sources": len(SOURCES),
                "lemma_hit_anchors": snap.get("lemma_hit_anchors"),
                "lemma_edges": snap.get("lemma_manifest_edge_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
