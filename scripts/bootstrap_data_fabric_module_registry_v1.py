#!/usr/bin/env python3
"""Bootstrap data_fabric_module_registry_v1_latest.json (M0–M4 rows, DF-P1-04 seed)."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/data_fabric_module_registry_v1_latest.json"

MODULES = [
    ("M0", "corpus_manifest", "scripts/build_logos_corpus_manifest_v1.py"),
    ("M1", "graph_slice", "scripts/build_showroom_meaning_topology_graph_slice_v1.py"),
    ("M2", "graph_wire_poc", "scripts/build_mkm_graph_wire_rag_poc_v1.py"),
    ("M3", "wire_envelope", "scripts/mkm_inter_agent_wire_envelope_v1.py"),
    ("M4", "oracle_v6_link", "docs/final/artifacts/logos_observatory_v6_poc_link_spec_v1.json"),
    ("M5", "seed_chain", "scripts/run_logos_graph_seed_chain_v1.py"),
    ("M6", "selective_corpus_load", "scripts/load_verse_corpus_by_ids_v1.py"),
    ("M7", "wire_profile_chain", "scripts/build_logos_graph_wire_profile_v1.py"),
    ("M8", "unified_asset_registry", "scripts/mkm_unified_asset_registry_v1.py"),
    ("M9", "atom_anchor_verse_pool", "scripts/resolve_logos_atom_anchor_verse_pool_v1.py"),
    ("M10", "canon_manuscript_fabric_v2", "scripts/build_logos_canon_manuscript_fabric_v2.py"),
    ("M11", "corpus_regime_singularity", "scripts/run_logos_corpus_regime_singularity_report_v1.py"),
    ("M12", "graph_expand_batch", "scripts/run_logos_graph_expand_batch_v1.py"),
    ("M13", "graph_regime_highlight", "scripts/build_logos_graph_regime_highlight_v1.py"),
    ("M14", "decoy_experience_layer", "scripts/bootstrap_decoy_experience_zone_shards_v1.py"),
    ("M15", "decoy_d1_mkmlife_route", "scripts/check_decoy_d1_mkmlife_readiness_v1.py"),
]


def _sha16(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16].upper()


def main() -> int:
    rows = []
    for mid, role, rel in MODULES:
        p = ROOT / rel.replace("/", "\\") if "\\" in rel else ROOT / rel
        rows.append(
            {
                "module_id": mid,
                "role": role,
                "script_or_artifact": rel.replace("\\", "/"),
                "exists": p.is_file(),
                "sha256_prefix": _sha16(p),
            }
        )
    doc = {
        "schema": "data_fabric_module_registry_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "modules": rows,
        "boundary_ack": "Bootstrap registry only; not 31k load or Track A promotion.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "count": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
