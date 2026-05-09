#!/usr/bin/env python3
"""Build public graph response from Logos ontology registry (NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
SCHEMA_PATH = ART / "schemas" / "public_graph_response_v1.schema.json"
DEFAULT_ONTOLOGY = ART / "logos_ontology_registry_v1_latest.json"
DEFAULT_OUT = ART / "public_graph_response_v1_latest.json"


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _slug(s: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._:-]+", "-", s.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "x"


def _confidence_from_tension(tension: float) -> str:
    if tension <= 0.35:
        return "A"
    if tension <= 0.7:
        return "B"
    return "C"


def _weight_bucket(v: float) -> str:
    if v < 0.33:
        return "low"
    if v < 0.67:
        return "mid"
    return "high"


def _safe_node_id(prefix: str, value: str) -> str:
    return f"n.{prefix}.{_slug(value)}"


def build_graph(ontology: dict[str, Any]) -> dict[str, Any]:
    obs = ontology.get("observation") if isinstance(ontology.get("observation"), dict) else {}
    entities = ontology.get("entities") if isinstance(ontology.get("entities"), dict) else {}
    relations = ontology.get("relations") if isinstance(ontology.get("relations"), list) else []
    templates = ontology.get("render_templates") if isinstance(ontology.get("render_templates"), list) else []

    tension = float(obs.get("tension_score") or 0.0)
    conf = _confidence_from_tension(tension)
    regime = str(obs.get("regime") or "unknown")
    phase = str(obs.get("phase_label") or "phase")

    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    atom_to_node: dict[str, str] = {}

    for atom in entities.get("atoms") if isinstance(entities.get("atoms"), list) else []:
        if not isinstance(atom, dict):
            continue
        atom_id = str(atom.get("atom_id") or "")
        label = str(atom.get("label") or atom_id or "atom")
        nid = _safe_node_id("atom", atom_id or label)
        atom_to_node[atom_id] = nid
        if nid in node_ids:
            continue
        node_ids.add(nid)
        nodes.append(
            {
                "node_id_public": nid,
                "anchor_ref": f"ATOM:{atom_id or _slug(label)}",
                "theme_tag": _slug(label),
                "confidence_band": conf,
            }
        )

    for root in entities.get("morphology_roots") if isinstance(entities.get("morphology_roots"), list) else []:
        if not isinstance(root, dict):
            continue
        strongs = str(root.get("strongs_code") or "H0000")
        ref = str(root.get("canonical_reference") or "UNVERIFIED_REF")
        nid = _safe_node_id("strong", strongs)
        if nid in node_ids:
            continue
        node_ids.add(nid)
        nodes.append(
            {
                "node_id_public": nid,
                "anchor_ref": ref[:64],
                "theme_tag": "morphology_root",
                "confidence_band": "A" if strongs != "H0000" else "C",
            }
        )

    metaphor_to_node: dict[str, str] = {}
    for row in templates:
        if not isinstance(row, dict):
            continue
        key = str(row.get("metaphor_key") or "")
        if not key:
            continue
        nid = _safe_node_id("metaphor", key)
        metaphor_to_node[key] = nid
        if nid in node_ids:
            continue
        node_ids.add(nid)
        nodes.append(
            {
                "node_id_public": nid,
                "anchor_ref": f"REGIME:{regime}",
                "theme_tag": _slug(key),
                "confidence_band": conf,
            }
        )

    phase_node_id = _safe_node_id("phase", phase)
    if phase_node_id not in node_ids:
        node_ids.add(phase_node_id)
        nodes.append(
            {
                "node_id_public": phase_node_id,
                "anchor_ref": f"REGIME:{regime}",
                "theme_tag": _slug(phase),
                "confidence_band": conf,
            }
        )

    edges: list[dict[str, Any]] = []
    edge_seen: set[tuple[str, str, str]] = set()
    for rel in relations:
        if not isinstance(rel, dict):
            continue
        key = str(rel.get("metaphor_key") or "")
        tgt = metaphor_to_node.get(key, phase_node_id)
        src_atoms = rel.get("then_atoms") if isinstance(rel.get("then_atoms"), list) else []
        for a in src_atoms:
            src = atom_to_node.get(str(a))
            if not src:
                continue
            sig = (src, tgt, "contextual")
            if sig in edge_seen:
                continue
            edge_seen.add(sig)
            edges.append(
                {
                    "source_node_id_public": src,
                    "target_node_id_public": tgt,
                    "edge_type": "contextual",
                    "weight_bucket": _weight_bucket(tension),
                }
            )
        sig2 = (phase_node_id, tgt, "semantic")
        if sig2 not in edge_seen and phase_node_id != tgt:
            edge_seen.add(sig2)
            edges.append(
                {
                    "source_node_id_public": phase_node_id,
                    "target_node_id_public": tgt,
                    "edge_type": "semantic",
                    "weight_bucket": _weight_bucket(float(obs.get("similarity_0_1") or 0.0)),
                }
            )

    insights: list[dict[str, Any]] = []
    tpl_by_key = {str(x.get("metaphor_key")): x for x in templates if isinstance(x, dict)}
    for idx, rel in enumerate(relations, start=1):
        if not isinstance(rel, dict):
            continue
        key = str(rel.get("metaphor_key") or "metaphor")
        tpl = tpl_by_key.get(key, {})
        template = str(tpl.get("template") or f"{key} interpretation")
        footer = str(tpl.get("non_gating_footer") or "[NON_GATING] research only.")
        fals = rel.get("falsification_trigger") if isinstance(rel.get("falsification_trigger"), list) else []
        fals_line = f" Falsification: {fals[0]}" if fals else ""
        insights.append(
            {
                "insight_id": f"ins.{_now_date()}.{idx:03d}",
                "anchor_ref": f"REGIME:{regime}",
                "theme_tag": _slug(key),
                "insight_summary": f"{template}{fals_line} {footer}",
                "confidence_band": conf,
            }
        )

    return {
        "schema": "public_graph_response_v1",
        "version": "1.0.0",
        "policy_label": "NON_GATING",
        "research_only": True,
        "no_trading_advice": True,
        "as_of_date": _now_date(),
        "pagination": {"limit": 20, "next_cursor": None},
        "nodes": nodes,
        "edges": edges,
        "insights": insights,
    }


def _validate_schema(doc: dict[str, Any], schema_path: Path) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise RuntimeError("jsonschema package required for validation") from exc
    schema = _read_json(schema_path)
    validator = Draft202012Validator(schema)
    errs = list(validator.iter_errors(doc))
    if errs:
        msg = "; ".join(f"{e.message} at {'/'.join(str(x) for x in e.path)}" for e in errs[:5])
        raise ValueError(f"public_graph schema validation failed: {msg}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ontology-json", type=Path, default=DEFAULT_ONTOLOGY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--schema-json", type=Path, default=SCHEMA_PATH)
    args = ap.parse_args()

    ont_path = args.ontology_json if args.ontology_json.is_absolute() else ROOT / args.ontology_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    schema_path = args.schema_json if args.schema_json.is_absolute() else ROOT / args.schema_json
    if not ont_path.is_file():
        raise SystemExit(f"Missing --ontology-json: {ont_path}")
    if not schema_path.is_file():
        raise SystemExit(f"Missing --schema-json: {schema_path}")

    ontology = _read_json(ont_path)
    doc = build_graph(ontology)
    _validate_schema(doc, schema_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "nodes": len(doc["nodes"]), "edges": len(doc["edges"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
