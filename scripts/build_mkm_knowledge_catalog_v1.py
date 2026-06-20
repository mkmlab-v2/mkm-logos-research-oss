#!/usr/bin/env python3
"""Federated knowledge catalog — read-only merge of Vault 1–4 pointers ([HYPO]).

Does NOT merge reference bodies into ops_memory_index.

  py scripts/build_mkm_knowledge_catalog_v1.py
  py scripts/build_mkm_knowledge_catalog_v1.py --stdout-only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = SCRIPT_ROOT / "docs/final/artifacts/mkm_knowledge_catalog_v1_latest.json"
OPS_INDEX = SCRIPT_ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
LTM_GRAPH = SCRIPT_ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json"
REF_REGISTRY = SCRIPT_ROOT / "storage/meta/mkm_reference_pointer_registry_v1.json"
RESUME_PACK = SCRIPT_ROOT / "docs/final/artifacts/mkm_chat_resume_pack_latest.json"
WIKI_RAW = SCRIPT_ROOT / "memory/obsidian_vault/llm_wiki/raw"
CHECK_REGISTRY = SCRIPT_ROOT / "scripts/check_mkm_reference_pointer_registry_v1.py"
MERGED_LIT_REVIEW = SCRIPT_ROOT / "docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md"
MERGED_GATE_CHAIN = SCRIPT_ROOT / "scripts/run_mkm_merged_lit_review_gate_chain_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _ltm_graph_node_count(doc: dict[str, Any] | None) -> int:
    if not doc:
        return 0
    for key in ("concepts", "nodes"):
        nodes = doc.get(key)
        if isinstance(nodes, dict):
            return len(nodes)
        if isinstance(nodes, list):
            return len(nodes)
    return 0


def build_catalog(root: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(CHECK_REGISTRY), "--workspace-root", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    registry_gate_ok = proc.returncode == 0
    registry_gate_detail = (proc.stdout or proc.stderr).strip()

    ops_doc = _load_json(OPS_INDEX)
    ltm_doc = _load_json(LTM_GRAPH)
    ref_doc = _load_json(REF_REGISTRY)
    resume_doc = _load_json(RESUME_PACK)

    pointers = (ref_doc or {}).get("pointers") or []
    wiki_raw_count = len(list(WIKI_RAW.glob("*.md"))) if WIKI_RAW.is_dir() else 0

    pointer_summaries = [
        {
            "id": p.get("id"),
            "resource_path": p.get("resource_path"),
            "repo_path": p.get("repo_path"),
            "domain_tags": p.get("domain_tags"),
            "akl_status": p.get("akl_status"),
            "inject_policy": p.get("inject_policy"),
        }
        for p in pointers
    ]

    return {
        "schema": "mkm_knowledge_catalog_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] federated catalog — pointer merge only; no ops index body ingest",
        "generated_at_utc": _utc_now(),
        "registry_gate_ok": registry_gate_ok,
        "registry_gate_detail": registry_gate_detail,
        "vaults": {
            "governance_ltm": {
                "ops_index_path": "storage/meta/mkm_ops_memory_index_v1.json",
                "ops_node_count": len((ops_doc or {}).get("nodes") or {}),
                "ltm_graph_path": "storage/meta/mkm_long_term_memory_graph_v1.json",
                "ltm_graph_node_count": _ltm_graph_node_count(ltm_doc),
                "resume_pack_path": "docs/final/artifacts/mkm_chat_resume_pack_latest.json",
                "resume_pack_present": resume_doc is not None,
            },
            "reference_cold": {
                "registry_path": "storage/meta/mkm_reference_pointer_registry_v1.json",
                "pointer_count": len(pointers),
            },
            "shallow_tau": {
                "resume_pack_path": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
                "cursor_atdocs_pattern": "@docs/<resource_path>",
            },
            "query_rag": {
                "llm_wiki_raw_dir": "memory/obsidian_vault/llm_wiki/raw",
                "llm_wiki_raw_count": wiki_raw_count,
            },
        },
        "reference_pointers": pointer_summaries,
        "research_ssot": {
            "merged_lit_review_path": "docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md",
            "merged_lit_review_present": MERGED_LIT_REVIEW.is_file(),
            "registry_pointer_id": "ref:research:nextgen_hybrid_merged",
            "gate_chain_script": "scripts/run_mkm_merged_lit_review_gate_chain_v1.py",
            "gate_chain_present": MERGED_GATE_CHAIN.is_file(),
        },
        "reproduce": {
            "validate_registry": "py scripts/check_mkm_reference_pointer_registry_v1.py",
            "build_catalog": "py scripts/build_mkm_knowledge_catalog_v1.py",
            "merged_gate_chain": (
                "py scripts/run_mkm_merged_lit_review_gate_chain_v1.py "
                "--input docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md"
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    doc = build_catalog(root)
    if not doc.get("registry_gate_ok"):
        print(doc.get("registry_gate_detail") or "registry gate failed", file=sys.stderr)
        return 1

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(payload, end="")
        return 0

    out_path = args.out if args.out.is_absolute() else root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(f"pointers={doc['vaults']['reference_cold']['pointer_count']} wiki_raw={doc['vaults']['query_rag']['llm_wiki_raw_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
