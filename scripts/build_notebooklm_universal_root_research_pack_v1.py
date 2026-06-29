#!/usr/bin/env python3
"""Build NotebookLM upload pack for 14-universal-lexicon-dr research sandbox [HYPO]."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "notebooklm_universal_root_research_pack_v1"
DEFAULT_MANIFEST = ROOT / "reports" / "notebooklm_universal_root_research_pack_v1_latest.json"

PACK_FILES: list[str] = [
    "docs/research/raw/universal_root_lexicon_matrix_gemini_prompt_v1.md",
    "docs/research/raw/universal_root_lexicon_matrix_gemini_report_2026-06-21.md",
    "docs/research/raw/universal_root_lexicon_matrix_cursor_sweep_2026-06-21.md",
    "docs/research/UNIVERSAL_ROOT_LEXICON_MATRIX_MERGED_LIT_REVIEW_2026-06-21.md",
    "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json",
    "docs/final/artifacts/universal_root_research_impl_bridge_v1_latest.json",
    "reports/logos_graphrag_phase11n_fact_support_gate_chain_v1_latest.json",
    "reports/logos_graphrag_phase11q_compress_parity_chain_v1_latest.json",
    "reports/logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1_latest.json",
    "reports/deepnsm_hf_ab_research_stub_v1_latest.json",
    "reports/deepnsm_hf_explication_chain_v1_latest.json",
    "reports/logos_graphrag_phase11s_evidence_nl_sync_chain_v1_latest.json",
    "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json",
    "reports/logos_graphrag_phase12_live_public_chain_v1_latest.json",
    "reports/logos_phase12_live_bundle_v1_latest.json",
    "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json",
    "reports/logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1_latest.json",
    "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json",
    "reports/deepnsm_hf_stub_vs_ollama_500_ab_v1_latest.json",
    "reports/logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1_latest.json",
    "reports/logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1_latest.json",
    "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json",
    "reports/deepnsm_hf_ollama_vs_checkpoint_ab_v1_latest.json",
    "reports/logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json",
    "reports/universal_root_topology_crosswalk_v1_latest.json",
    "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json",
    "reports/logos_graphrag_phase17_closure_observability_chain_v1_latest.json",
    "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json",
    "reports/universal_root_topology_crosswalk_gate_v1_latest.json",
    "reports/logos_oracle_narrative_closure_observability_chain_v1_latest.json",
    "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json",
]

# Phase 17 delta push: re-upload changed SSOT with fresh NL titles (no full prune).
DELTA_PHASE17_PACK_NAMES: frozenset[str] = frozenset(
    {
        "docs__final__artifacts__UNIVERSAL_ROOT_GATE_SPEC_V1.json",
        "docs__final__artifacts__logos_graphrag_bridge_evidence_pack_v1_latest.json",
        "reports__logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json",
        "reports__universal_root_topology_crosswalk_v1_latest.json",
        "docs__final__artifacts__UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json",
        "reports__logos_graphrag_phase17_closure_observability_chain_v1_latest.json",
        "docs__final__artifacts__UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json",
        "reports__universal_root_topology_crosswalk_gate_v1_latest.json",
        "reports__logos_oracle_narrative_closure_observability_chain_v1_latest.json",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build_pack(*, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    for rel in PACK_FILES:
        src = ROOT / rel.replace("/", "\\")
        if not src.is_file():
            entries.append({"source_path": rel, "exists": False, "copied": False})
            continue
        safe_name = rel.replace("/", "__").replace("\\", "__")
        dst = out_dir / safe_name
        shutil.copy2(src, dst)
        entries.append(
            {
                "source_path": rel.replace("\\", "/"),
                "pack_name": safe_name,
                "exists": True,
                "copied": True,
                "bytes": dst.stat().st_size,
                "sha256": _sha256(dst),
            }
        )
    copied = [e for e in entries if e.get("copied")]
    return {
        "schema": "notebooklm_universal_root_research_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "notebook_mcp_id": "14-universal-lexicon-dr",
        "pack_dir": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
        "file_count": len(copied),
        "entries": entries,
        "reproduce": "py scripts/build_notebooklm_universal_root_research_pack_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    doc = build_pack(out_dir=args.out_dir)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["file_count"] > 0,
                "file_count": doc["file_count"],
                "manifest": str(args.manifest),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["file_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
