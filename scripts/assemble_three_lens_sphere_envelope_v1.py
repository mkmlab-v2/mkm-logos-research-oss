#!/usr/bin/env python3
"""O-P30 Phase 0: read-only three-lens magic sphere envelope for mkmlife + jemaai hub.

Does not run GraphRAG or train models. Merges existing *_latest.json pointers only.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FUSION = ROOT / "docs/final/artifacts/independent_lens_fusion_stub_latest.json"
DEFAULT_PROPHECY = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_TOPOLOGY = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_CDI = ROOT / "docs/final/artifacts/logos_cross_domain_interface_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/three_lens_sphere_envelope_v1.schema.json"
MKMLIFE_PUBLIC_LEGACY = ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_v1.json"
MKMLIFE_PUBLIC_LOGOS = ROOT / "projects/mkm/mkm-life/public/data/three_lens_sphere_envelope_public_v1.json"
MKMLIFE_INTERNAL = ROOT / "projects/mkm/mkm-life/data/internal/three_lens_sphere_envelope_v1.json"

HUB_V6 = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"
HUB_TOPOLOGY = "https://jemaai.cloud/public_showroom_meaning_topology_graph_v1.html"
HUB_MKMLIFE = "https://mkmlife.com/oracle-sphere"

VERSION = "1.0.0"

# LOGOS-100PCT: tag → (artifact path under ROOT, optional invoke script)
RAG_LAYER_REGISTRY: dict[str, list[tuple[str, Path, str | None]]] = {
    "lexical": [
        (
            "logos_semantic_query_set_v3_bilingual_v1",
            ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json",
            "scripts/bootstrap_logos_query_gold_human_v1.py",
        ),
        (
            "strongs_ko_only_mapper",
            ROOT / "docs/final/artifacts/logos_semantic_query_set_v3_bilingual_v1.json",
            "scripts/logos_rag_query_route_v1.py",
        ),
        (
            "logos_semantic_query_gold_human",
            ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json",
            "scripts/apply_logos_rag_q01_theology_primary_order_v1.py",
        ),
    ],
    "semantic": [
        (
            "logos_independent_lens_v0",
            ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
            "scripts/run_lens_logos.py",
        ),
        (
            "btrack_st_vector_index",
            ROOT / "reports/constitution/btrack_pilot/logos_vector_index_ann_lite_st_u_v1.sqlite",
            "scripts/logos_ann_lite_embedding_v1.py",
        ),
        (
            "logos_concept_bridge_registry",
            ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
            "scripts/build_logos_concept_bridge_registry_v1.py",
        ),
        (
            "logos_rag_dual_gold_eval",
            ROOT / "reports/constitution/btrack_pilot/comp_logos_rag_dual_gold_eval_v1_latest.json",
            "scripts/run_logos_rag_dual_gold_eval_v1.py",
        ),
    ],
    "temporal": [
        (
            "logos_chronology_overlay",
            ROOT
            / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_chronology_overlay_v1.json",
            "scripts/merge_logos_chronology_era_presets_v1.py",
        ),
        (
            "myeongni_session_panel",
            ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "scripts/build_btrack_session_instant_myeongni_panel_v1.py",
        ),
    ],
    "constitutional": [
        (
            "regime_map_primary",
            ROOT / "data/regimes/regime_map.json",
            None,
        ),
        (
            "market_sasang_veto_shadow",
            ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json",
            "scripts/run_market_sasang_lens_v1.py",
        ),
    ],
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _manifest(path: Path) -> dict[str, Any]:
    return {"path": _rel(path), "present": path.is_file()}


def _build_rag_layers_resolved() -> dict[str, list[dict[str, Any]]]:
    ts = _now_utc()
    out: dict[str, list[dict[str, Any]]] = {}
    for layer, entries in RAG_LAYER_REGISTRY.items():
        resolved: list[dict[str, Any]] = []
        for tag, artifact_path, script_rel in entries:
            present = artifact_path.is_file()
            entry: dict[str, Any] = {
                "tag": tag,
                "artifact_path": _rel(artifact_path),
                "present": present,
                "resolved_at_utc": ts,
            }
            if script_rel:
                script_path = ROOT / script_rel
                entry["script_path"] = _rel(script_path) if script_path.is_file() else script_rel
                entry["script_present"] = script_path.is_file()
            resolved.append(entry)
        out[layer] = resolved
    return out


def _find_lens_input(fusion: dict[str, Any], lens_id: str) -> dict[str, Any] | None:
    for row in fusion.get("inputs") or []:
        if isinstance(row, dict) and row.get("lens_id") == lens_id:
            return row
    return None


def _body_from_lens(lens_id: str, row: dict[str, Any] | None, lens_doc: dict[str, Any] | None) -> str:
    if row and not row.get("available"):
        return "렌즈 산출물 없음 · 관측 스킵."
    parts: list[str] = []
    if lens_doc:
        snippet = lens_doc.get("narrative_snippet_guarded") or lens_doc.get("narrative_snippet")
        if snippet:
            parts.append(str(snippet)[:400])
    if row:
        sign = row.get("direction_sign")
        score = row.get("direction_score")
        conf = row.get("confidence")
        if sign is not None:
            parts.append(f"방향 sign={sign} score={score} conf={conf}")
    csum = ""
    if lens_id == "logos":
        return (
            "[NON_GATING] 성경·연대기 축 보조 해설. "
            + (" ".join(parts) if parts else "evidence_refs만 연결.")
            + " 투자·실매매 근거 아님."
        )
    if lens_id == "sasang":
        ms = row.get("market_sasang_lens_v1") if row else None
        if isinstance(ms, dict) and ms.get("veto_force_hold"):
            codes = ms.get("veto_reason_codes") or []
            parts.append(f"Veto 신호광(관측): {','.join(str(c) for c in codes[:3])}")
        return (
            "4체질 에너지·편향 관측(연구). "
            + (" ".join(parts) if parts else "독립 렌즈 스텁.")
            + " 의료·처방 아님."
        )
    if lens_id == "myeongni":
        return (
            "만세력·시간 주기 관측(결정론 엔진 별도). "
            + (" ".join(parts) if parts else "명리 독립 렌즈.")
            + " 확정 예언·주문 트리거 아님."
        )
    return " ".join(parts) if parts else "관측 스텁."


def _final_action(fusion: dict[str, Any]) -> str:
    csum = fusion.get("conflict_summary") if isinstance(fusion.get("conflict_summary"), dict) else {}
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    conflict_count = int(consensus.get("conflict_count") or 0)
    ms_row = _find_lens_input(fusion, "market_sasang")
    if isinstance(ms_row, dict):
        ms = ms_row.get("market_sasang_lens_v1")
        if isinstance(ms, dict) and ms.get("veto_force_hold"):
            return "REDUCE"
    if conflict_count >= 1:
        return "WATCH"
    return "HOLD"


def assemble(
    fusion_path: Path,
    prophecy_path: Path,
    topology_path: Path,
    cdi_path: Path,
) -> dict[str, Any]:
    fusion = _read_json(fusion_path)
    if not fusion:
        raise SystemExit(f"Missing or invalid fusion JSON: {fusion_path}")

    prophecy = _read_json(prophecy_path) or {}
    topology = _read_json(topology_path) or {}
    cdi = _read_json(cdi_path)

    logos_row = _find_lens_input(fusion, "logos")
    sasang_row = _find_lens_input(fusion, "sasang")
    myeongni_row = _find_lens_input(fusion, "myeongni")

    logos_doc = _read_json(ROOT / "docs/final/artifacts/logos_independent_lens_latest.json")
    sasang_doc = _read_json(ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json")
    myeongni_doc = _read_json(ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json")

    metrics = prophecy.get("metrics") if isinstance(prophecy.get("metrics"), dict) else {}
    headline_rate = metrics.get("price_directional_hit_rate")
    selection = topology.get("selection") if isinstance(topology.get("selection"), dict) else {}
    node_count = int(selection.get("node_count") or selection.get("max_nodes") or 0)
    csum = fusion.get("conflict_summary") if isinstance(fusion.get("conflict_summary"), dict) else {}
    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}

    regime_id = "observational_btrack"
    if cdi and cdi.get("field_regime_id"):
        regime_id = str(cdi.get("field_regime_id"))

    envelope: dict[str, Any] = {
        "schema": "three_lens_sphere_envelope_v1",
        "version": VERSION,
        "ts_utc": _now_utc(),
        "labels": ["HYPO", "NON_GATING", "research_only"],
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "field": {
            "regime_id": regime_id,
            "regime_label_ko": "1차 실물 레짐·예언 헤드라인 관측 (게이트 별도)",
            "evidence_path": _rel(prophecy_path),
            "prophecy_headline_active_rate": headline_rate,
        },
        "lenses": {
            "logos": {
                "available": bool(logos_row and logos_row.get("available")),
                "title_ko": "성경 · 연대기 축",
                "body_ko": _body_from_lens("logos", logos_row, logos_doc),
                "direction_sign": (logos_row or {}).get("direction_sign"),
                "confidence": (logos_row or {}).get("confidence"),
                "non_gating": True,
                "artifact_path": _rel(ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"),
                "evidence_tier": "hypo_research_only",
            },
            "sasang": {
                "available": bool(sasang_row and sasang_row.get("available")),
                "title_ko": "사상 · 4체질",
                "body_ko": _body_from_lens("sasang", sasang_row, sasang_doc),
                "direction_sign": (sasang_row or {}).get("direction_sign"),
                "confidence": (sasang_row or {}).get("confidence"),
                "non_gating": True,
                "artifact_path": _rel(ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"),
                "evidence_tier": "hypo_research_only",
            },
            "myeongni": {
                "available": bool(myeongni_row and myeongni_row.get("available")),
                "title_ko": "명리 · 시간 주기",
                "body_ko": _body_from_lens("myeongni", myeongni_row, myeongni_doc),
                "direction_sign": (myeongni_row or {}).get("direction_sign"),
                "confidence": (myeongni_row or {}).get("confidence"),
                "non_gating": True,
                "artifact_path": _rel(ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"),
                "evidence_tier": "hypo_research_only",
            },
        },
        "conflict_resolver": {
            "summary_ko": str(csum.get("conflict_narrative_guarded") or "")[:600],
            "minority_lens_ids": list(csum.get("minority_lens_ids") or []),
            "agreement_rate": float(consensus.get("agreement_rate") or 0.0),
            "conflict_count": int(consensus.get("conflict_count") or 0),
        },
        "final_action": _final_action(fusion),
        "hub_links": {
            "jemaai_logos_v6_product": HUB_V6,
            "jemaai_meaning_topology_graph": HUB_TOPOLOGY,
            "mkmlife_oracle_sphere": HUB_MKMLIFE,
        },
        "graph_viz": {
            "node_count_display": node_count,
            "graph_slice_path": _rel(topology_path),
        },
        "rag_layers": {
            "lexical": [t[0] for t in RAG_LAYER_REGISTRY["lexical"]],
            "semantic": [t[0] for t in RAG_LAYER_REGISTRY["semantic"]],
            "temporal": [t[0] for t in RAG_LAYER_REGISTRY["temporal"]],
            "constitutional": [t[0] for t in RAG_LAYER_REGISTRY["constitutional"]],
        },
        "rag_layers_resolved": _build_rag_layers_resolved(),
        "inputs_manifest": [
            _manifest(fusion_path),
            _manifest(prophecy_path),
            _manifest(topology_path),
            _manifest(cdi_path),
            _manifest(ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"),
            _manifest(ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"),
            _manifest(ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"),
            _manifest(ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"),
            _manifest(
                ROOT / "reports/constitution/btrack_pilot/comp_logos_rag_dual_gold_eval_v1_latest.json"
            ),
            _manifest(ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"),
            _manifest(ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json"),
        ],
    }
    return envelope


def strip_public_envelope(full: dict[str, Any]) -> dict[str, Any]:
    """Public oracle-sphere: Logos axis only — hide myeongni/sasang IP and internal paths."""
    logos = dict((full.get("lenses") or {}).get("logos") or {})
    for key in ("artifact_path",):
        logos.pop(key, None)
    public: dict[str, Any] = {
        k: v
        for k, v in full.items()
        if k
        not in (
            "lenses",
            "inputs_manifest",
            "rag_layers",
            "rag_layers_resolved",
        )
    }
    public["profile_mode"] = "public_logos_only"
    public["exposure_tier"] = "public_demo"
    public["lenses"] = {"logos": logos}
    public["layer_b_explore"] = {
        "default_enabled": False,
        "enable_query_flag": "explore",
        "rag_graph_runtime": False,
    }
    graph_viz = dict(public.get("graph_viz") or {})
    graph_viz.pop("graph_slice_path", None)
    public["graph_viz"] = graph_viz
    return public


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble three-lens magic sphere envelope v1 (read-only).")
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--prophecy-json", type=Path, default=DEFAULT_PROPHECY)
    ap.add_argument("--topology-json", type=Path, default=DEFAULT_TOPOLOGY)
    ap.add_argument("--cdi-json", type=Path, default=DEFAULT_CDI)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--copy-mkmlife-public", action="store_true")
    ap.add_argument("--validate-schema", action="store_true")
    args = ap.parse_args()

    envelope = assemble(args.fusion_json, args.prophecy_json, args.topology_json, args.cdi_json)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_rel(args.out_json)} final_action={envelope['final_action']}")

    if args.copy_mkmlife_public:
        MKMLIFE_INTERNAL.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_INTERNAL.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {_rel(MKMLIFE_INTERNAL)} (internal full envelope)")
        public = strip_public_envelope(envelope)
        MKMLIFE_PUBLIC_LOGOS.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_PUBLIC_LOGOS.write_text(
            json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {_rel(MKMLIFE_PUBLIC_LOGOS)} (public Logos-only)")
        if MKMLIFE_PUBLIC_LEGACY.is_file():
            MKMLIFE_PUBLIC_LEGACY.unlink()
            print(f"Removed legacy {_rel(MKMLIFE_PUBLIC_LEGACY)}")

    if args.validate_schema and SCHEMA_PATH.is_file():
        try:
            import jsonschema  # type: ignore

            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.validate(envelope, schema)
            print("Schema validation: OK")
        except ImportError:
            print("Schema validation skipped (jsonschema not installed)")
        except Exception as exc:
            raise SystemExit(f"Schema validation failed: {exc}") from exc


if __name__ == "__main__":
    main()
