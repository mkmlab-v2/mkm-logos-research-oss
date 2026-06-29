#!/usr/bin/env python3
"""Build public showroom subgraph GraphRAG audit slice for oracle v6 panel ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.showroom_public_export_guard_v1 import FORBIDDEN_KEY_SUBSTRINGS, scan_forbidden

DEFAULT_ROUTER = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"
DEFAULT_GOVERNANCE = ROOT / "reports/logos_concept_bridge_governance_v1_latest.json"
DEFAULT_LEMMA_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/showroom_logos_subgraph_audit_slice_v1.schema.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_subgraph_audit_slice_v1.json"
)
DEFAULT_MIRROR = ROOT / "docs/final/artifacts/showroom_logos_subgraph_audit_slice_v1_latest.json"

DISCLAIMER = {
    "evidence_tier": "hypo_research_only",
    "gating_status": "NON_GATING",
    "note_ko": (
        "Subgraph GraphRAG audit는 사전 계산된 라우터 스냅샷입니다. 실시간 LLM·예언 적중·"
        "Track A·실매매 트리거가 아닙니다. lemma/bridge 경로는 교육용 [HYPO]입니다."
    ),
    "note_ko_product": (
        "Precomputed subgraph router audit · research_only · NON_GATING · not investment advice · no live LLM."
    ),
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = _load(schema_path)
    jsonschema.Draft7Validator(schema).validate(doc)


def _paths_public(router: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        rows.append(
            {
                "path_id": path.get("path_id"),
                "steps": list(path.get("steps") or []),
                "note_ko": path.get("note_ko"),
                "match_score": path.get("match_score"),
            }
        )
    return rows


def _audit_rows(router: dict[str, Any], governance: dict[str, Any] | None, lemma: dict[str, Any] | None) -> list[list[str]]:
    summary = router.get("summary") if isinstance(router.get("summary"), dict) else {}
    lemma_meta = router.get("lemma_contain_meta") if isinstance(router.get("lemma_contain_meta"), dict) else {}
    rows = [
        ["Query (demo)", str(router.get("query") or "—")],
        ["Bridges matched", str(router.get("bridges_matched") or 0)],
        ["Paths returned", str(summary.get("paths") or len(router.get("paths") or []))],
        ["Distinct verse anchors", str(summary.get("verse_ids") or len(router.get("verse_ids") or []))],
        ["Lemma CONTAIN hits", str(summary.get("lemma_edge_hits") or len(router.get("lemma_edge_hits") or []))],
        ["Lemma edges considered", str(lemma_meta.get("edges_considered") or "—")],
        ["Router version", str(router.get("version") or "—")],
        ["Snapshot UTC", str(router.get("generated_at_utc") or "—")],
    ]
    if governance:
        rows.extend(
            [
                ["Human-reviewed bridges", f"{governance.get('human_reviewed_count')}/{governance.get('bridge_count')}"],
                ["Human-reviewed ratio", str(governance.get("human_reviewed_ratio") or "—")],
                ["LLM bridge count", str(governance.get("llm_bridge_count") or "—")],
            ]
        )
    if lemma:
        rows.append(["Lemma edge manifest count", str(lemma.get("edge_count") or "—")])
    return rows


def _public_router_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(summary, dict):
        return None
    out: dict[str, Any] = {}
    for key, val in summary.items():
        key_lower = str(key).lower()
        if any(sub in key_lower for sub in FORBIDDEN_KEY_SUBSTRINGS):
            continue
        out[key] = val
    return out


def build_slice(
    *,
    router_path: Path,
    governance_path: Path | None,
    lemma_manifest_path: Path | None,
) -> dict[str, Any]:
    if not router_path.is_file():
        raise FileNotFoundError(router_path)
    router = _load(router_path)
    policy = router.get("policy") if isinstance(router.get("policy"), dict) else {}
    if router.get("send_gate") not in (None, "HOLD") and policy.get("send_gate") not in (None, "HOLD"):
        raise ValueError("router send_gate must be HOLD")
    governance = _load(governance_path) if governance_path and governance_path.is_file() else None
    lemma = _load(lemma_manifest_path) if lemma_manifest_path and lemma_manifest_path.is_file() else None

    return {
        "schema_version": "showroom_logos_subgraph_audit_slice_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "disclaimer": DISCLAIMER,
        "router_snapshot": {
            "query": router.get("query"),
            "bridges_matched": router.get("bridges_matched"),
            "theme_lanes_active": list(router.get("theme_lanes_active") or []),
            "path_count": len(router.get("paths") or []),
            "verse_id_count": len(router.get("verse_ids") or []),
            "lemma_edge_hit_count": len(router.get("lemma_edge_hits") or []),
            "lemma_contain_meta": router.get("lemma_contain_meta"),
            "summary": _public_router_summary(router.get("summary")),
            "router_generated_at_utc": router.get("generated_at_utc"),
        },
        "governance_snapshot": {
            "human_reviewed_ratio": (governance or {}).get("human_reviewed_ratio"),
            "human_reviewed_count": (governance or {}).get("human_reviewed_count"),
            "bridge_count": (governance or {}).get("bridge_count"),
            "llm_bridge_count": (governance or {}).get("llm_bridge_count"),
            "unsigned_bridge_count": (governance or {}).get("unsigned_bridge_count"),
        }
        if governance
        else None,
        "lemma_manifest_snapshot": {
            "edge_count": (lemma or {}).get("edge_count"),
            "bridge_sources_count": (lemma or {}).get("bridge_sources_count"),
            "dropped_not_in_corpus_count": (lemma or {}).get("dropped_not_in_corpus_count"),
        }
        if lemma
        else None,
        "paths_public": _paths_public(router),
        "audit_rows": _audit_rows(router, governance, lemma),
        "reproduce": "showroom_logos_subgraph_audit_slice_v1 builder",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOVERNANCE)
    ap.add_argument("--lemma-manifest-json", type=Path, default=DEFAULT_LEMMA_MANIFEST)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mirror-artifact", type=Path, default=DEFAULT_MIRROR)
    ap.add_argument("--no-mirror-artifact", action="store_true")
    args = ap.parse_args()

    if not args.schema.is_file():
        print(f"schema missing: {args.schema}", file=sys.stderr)
        return 2

    try:
        doc = build_slice(
            router_path=args.router_json,
            governance_path=args.governance_json,
            lemma_manifest_path=args.lemma_manifest_json,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    violations = scan_forbidden(doc)
    if violations:
        print("export guard failed:", file=sys.stderr)
        print("\n".join(violations[:20]), file=sys.stderr)
        return 1

    try:
        _validate(doc, args.schema)
    except Exception as exc:  # noqa: BLE001
        print(f"schema validation failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "path_count": doc["router_snapshot"]["path_count"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )

    if not args.no_mirror_artifact and args.mirror_artifact:
        args.mirror_artifact.parent.mkdir(parents=True, exist_ok=True)
        args.mirror_artifact.write_text(text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
