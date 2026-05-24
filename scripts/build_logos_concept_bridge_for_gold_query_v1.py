#!/usr/bin/env python3
"""Build logos_concept_bridge_v1 for a gold query id ([HYPO], Gemini + verse fallback)."""
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
ART = ROOT / "docs/final/artifacts"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
SCHEMA = "logos_concept_bridge_v1"

CONCEPT_SLUG: dict[str, str] = {
    "q02": "judgment_warning_collapse",
    "q05": "hope_prolonged_stress",
    "q06": "discipline_in_volatility",
    "q07": "restoration_after_disruption",
    "q09": "prudence_liquidity_stress",
    "q10": "resilience_capitulation_phase",
    "q11": "stability_after_volatility_shock",
    "q12": "risk_excess_cycle_unwind",
}

SKIP_BUILD: set[str] = {"q01", "q03", "q04", "q08"}  # dedicated bridge artifacts exist


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_gold_item(gold_path: Path, qid: str) -> dict[str, Any]:
    doc = json.loads(gold_path.read_text(encoding="utf-8-sig"))
    for it in doc.get("items") or []:
        if isinstance(it, dict) and str(it.get("id")) == qid:
            return it
    raise SystemExit(f"query id not found: {qid}")


def _verse_lang(verse_id: str) -> str:
    book = verse_id.split(".", 1)[0]
    if book in {"Matt", "Mark", "Luke", "John", "Acts", "Rom", "1Cor", "2Cor", "Gal", "Eph", "Phil", "Col", "1Thess", "2Thess", "1Tim", "2Tim", "Titus", "Phlm", "Heb", "Jas", "1Pet", "2Pet", "1John", "2John", "3John", "Jude", "Rev"}:
        return "greek"
    return "hebrew"


def _gold_verse_template(
    concept_ko: str, concept_id: str, verses: list[str], *, gold_query_id: str
) -> dict[str, Any]:
    pick = [v for v in verses if isinstance(v, str) and v.strip()][:3]
    if len(pick) < 3:
        pick = (pick + ["Ps.23.1", "Prov.3.5", "Isa.41.10"])[:3]
    nodes: list[dict[str, Any]] = [
        {
            "node_id": concept_id,
            "kind": "modern_concept",
            "label_ko": concept_ko,
            "label_en": concept_id.replace("concept:", "").replace("_", " "),
        }
    ]
    paths: list[dict[str, Any]] = []
    for i, vid in enumerate(pick):
        fn_id = f"function:theme_axis_{i + 1}"
        lemma_id = f"lemma:proxy:{i + 1}"
        verse_node = f"verse:{vid}"
        lang = _verse_lang(vid)
        nodes.extend(
            [
                {
                    "node_id": fn_id,
                    "kind": "function",
                    "label_ko": f"테마 축 {i + 1}",
                    "rationale_ko": f"gold human verse {vid}",
                },
                {
                    "node_id": lemma_id,
                    "kind": "lemma_proxy",
                    "label_ko": "lemma (proxy)",
                    "rationale_ko": "Educational anchor only",
                },
                {
                    "node_id": verse_node,
                    "kind": "verse_ref",
                    "verse_id": f"{lang}::{vid}",
                    "label_ko": vid,
                },
            ]
        )
        paths.append(
            {
                "path_id": f"path_gold_{i + 1}",
                "steps": [concept_id, fn_id, lemma_id, verse_node],
                "note_ko": f"gold align → {vid}",
            }
        )
    seeds = [f"{_verse_lang(v)}::{v}" for v in pick]
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "human_signoff_completed": False,
            "generation_method": "gold_verse_template_fallback_v1",
            "human_reviewed": False,
            "llm_api_called": False,
        },
        "query": {"concept_id": concept_id, "label_ko": concept_ko, "gold_query_id": gold_query_id},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {"seed_verse_ids": seeds},
        "known_limitations": [
            "Gold-verse template fallback; lemma_proxy not morphology-verified.",
            "Paths mirror logos_semantic_query_gold_human thematic labels only.",
        ],
    }


def _out_path(qid: str) -> Path:
    slug = CONCEPT_SLUG.get(qid, qid)
    return ART / f"logos_concept_bridge_gold_{qid}_{slug}_gemini_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query-id", required=True, help="e.g. q02")
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--template-only", action="store_true", help="Skip Gemini; write gold-verse template")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    qid = str(args.query_id).strip()
    if qid in SKIP_BUILD:
        print(json.dumps({"ok": True, "skipped": True, "reason": "dedicated_bridge_exists", "query_id": qid}))
        return 0

    item = _load_gold_item(args.gold_json, qid)
    concept_ko = str(item.get("query_ko") or "")
    slug = CONCEPT_SLUG.get(qid) or re.sub(r"[^a-z0-9]+", "_", str(item.get("query_en") or qid).lower()).strip("_")
    concept_id = f"concept:{slug}"
    out = args.output_json or _out_path(qid)
    verses = list(item.get("gold_verse_ids_human") or [])

    if args.template_only or args.dry_run:
        doc = _gold_verse_template(concept_ko, concept_id, verses, gold_query_id=qid)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"ok": True, "query_id": qid, "paths": len(doc["paths"]), "out": str(out), "template_only": True},
                ensure_ascii=False,
            )
        )
        return 0

    raw = ROOT / "reports/gemini_batch" / f"logos_concept_bridge_gold_{qid}_raw.txt"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/build_logos_concept_bridge_gemini_v1.py"),
        "--concept-ko",
        concept_ko,
        "--concept-id",
        concept_id,
        "--output-json",
        str(out),
        "--raw-out",
        str(raw),
        "--timeout",
        str(args.timeout),
    ]
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc != 0:
        doc = _gold_verse_template(concept_ko, concept_id, verses, gold_query_id=qid)
        doc["policy"]["generation_method"] = "gemini_error_gold_verse_fallback_v1"
        lim = doc.setdefault("known_limitations", [])
        if isinstance(lim, list):
            lim.append("Gemini subprocess failed; gold-verse template used.")
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "query_id": qid, "fallback": True, "out": str(out)}, ensure_ascii=False))
        return 0

    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    q = doc.setdefault("query", {})
    if isinstance(q, dict):
        q["gold_query_id"] = qid
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "query_id": qid,
                "paths": len(doc.get("paths") or []),
                "generation_method": (doc.get("policy") or {}).get("generation_method"),
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
