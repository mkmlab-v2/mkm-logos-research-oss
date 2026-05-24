"""Logos canon manuscript fabric v2 — address/ink separation + bridges + wire flags."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_logos_canon_manuscript_fabric_v2.py"
OUT = ROOT / "docs/final/artifacts/logos_canon_manuscript_fabric_v2_latest.json"
BRIDGES = ROOT / "data/logos/logos_variant_omission_bridge_edges_v2.jsonl"


def test_build_fabric_v2_smoke() -> None:
    if not (ROOT / "data/logos/logos_gap_mt_only_policy_v1.jsonl").is_file():
        return
    rc = subprocess.run(
        [sys.executable, str(BUILD)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert rc.returncode == 0, rc.stderr or rc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_canon_manuscript_fabric_v2"
    cal = doc["canonical_address_layer"]
    assert cal["verse_count"] == 31102
    assert cal["gap_nt_textual_variant_count"] == 15
    assert len(cal["gap_verse_ids"]) == 15
    assert doc["track_wall"]["core_corpus_sha_unchanged"] is True
    wire = doc["wire_routing"]["by_verse_id"]
    assert wire["Matt.18.11"]["routing_flags"] == 1
    assert BRIDGES.is_file()
    edges = [json.loads(line) for line in BRIDGES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(edges) == 15
    assert edges[0]["edge_type"] == "variant_omission_bridge_v2"


def test_resolve_manuscript_route() -> None:
    from scripts.logos_canon_manuscript_fabric_v2 import resolve_manuscript_route

    fabric = {
        "wire_routing": {
            "by_verse_id": {
                "Matt.18.11": {"routing_flags": 1},
            }
        }
    }
    gap = resolve_manuscript_route("Matt.18.11", fabric)
    assert gap["re_route_tr"] is True
    assert gap["route"] == "gap_textual_variant"
    ok = resolve_manuscript_route("Gen.1.1", fabric)
    assert ok["re_route_tr"] is False
    assert ok["route"] == "primary_sblgnt"


def test_wire_payload_enrichment() -> None:
    from scripts.logos_wire_manuscript_route_v1 import enrich_lexicon_wire_payload

    fabric = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {
        "wire_routing": {"by_verse_id": {"Matt.18.11": {"routing_flags": 1}}}
    }
    payload = {"schema": "mkm_lexicon_wire_v1", "atom_id_sequence": ["Matt.18.11"]}
    out = enrich_lexicon_wire_payload(payload, verse_id="Matt.18.11", fabric=fabric)
    assert out["routing_flags"] == 1
    assert out["manuscript_route"]["route"] == "gap_textual_variant"
