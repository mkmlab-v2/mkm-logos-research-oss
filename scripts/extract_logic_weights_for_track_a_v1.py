#!/usr/bin/env python3
"""Extract logic-aware shadow weights for Track A compression experiments.

This script is strictly NON_GATING / research_only and does not mutate Track A policy.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/tracka_logic_weights_shadow_v1_latest.json"
PATH_GATE_DEFAULT = ROOT / "reports/logos_path_verification_gate_v1_latest.json"
SHADOW_DEFAULT = ROOT / "reports/verse_metadata_shadow_v1_latest.json"
PSI_DEFAULT = ROOT / "reports/logos_psi_logic_extraction_v1_latest.json"

WORD_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]{2,}")

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "true",
    "false",
    "track",
    "read",
    "only",
    "actor",
    "phase",
    "gate",
    "logic",
    "path",
    "send",
    "open",
    "ready",
    "external",
    "human",
    "리포트",
    "작업",
    "구조",
    "검증",
    "합선",
    "금지",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _tokenize(text: str) -> list[str]:
    out: list[str] = []
    for m in WORD_RE.findall(text or ""):
        w = m.lower()
        if len(w) <= 1 or w in STOPWORDS:
            continue
        out.append(w)
    return out


def build(*, max_terms: int, path_gate: Path, shadow_path: Path, psi_path: Path) -> dict[str, Any]:
    gate = _load(path_gate)
    shadow = _load(shadow_path)
    psi = _load(psi_path)

    term_counter: Counter[str] = Counter()
    source_evidence: dict[str, dict[str, Any]] = {}

    # 1) From key-verse shadow rows (highest confidence first).
    for row in (shadow.get("rows") or []):
        conf = float(row.get("confidence") or 0.0)
        primary = str(row.get("primary_tag") or "")
        if conf <= 0:
            continue
        for t in _tokenize(primary):
            term_counter[t] += max(1, int(round(conf * 10)))
            source_evidence.setdefault(t, {"sources": set(), "count": 0})
            source_evidence[t]["sources"].add("verse_metadata_shadow")
            source_evidence[t]["count"] += 1

    # 2) From path gate units (citation-grounded lines).
    for chk in (gate.get("checks") or []):
        if chk.get("v_score") != 1:
            continue
        unit_id = str(chk.get("unit_id") or "")
        weight = 3 if "citation_lock" in str(chk.get("reason") or "") else 1
        for t in _tokenize(unit_id):
            term_counter[t] += weight
            source_evidence.setdefault(t, {"sources": set(), "count": 0})
            source_evidence[t]["sources"].add("path_gate")
            source_evidence[t]["count"] += 1

    # 3) From PSI logic graph source previews (structure-only transplant).
    graph = (psi.get("logic_graph") or {})
    for node in (graph.get("nodes") or []):
        preview = str(node.get("source_line_preview") or "")
        ntype = str(node.get("type") or "")
        base = 2 if ntype in {"Antecedent", "Consequent", "Constraints"} else 1
        for t in _tokenize(preview):
            term_counter[t] += base
            source_evidence.setdefault(t, {"sources": set(), "count": 0})
            source_evidence[t]["sources"].add("psi_logic_graph")
            source_evidence[t]["count"] += 1

    top_terms = term_counter.most_common(max(1, max_terms))
    max_score = float(top_terms[0][1]) if top_terms else 1.0

    weighted_terms: list[dict[str, Any]] = []
    for term, score in top_terms:
        ev = source_evidence.get(term) or {"sources": set(), "count": 0}
        weighted_terms.append(
            {
                "term": term,
                "weight": round(float(score), 4),
                "normalized_weight": round(float(score) / max_score, 6),
                "source_count": int(ev.get("count") or 0),
                "sources": sorted(ev.get("sources") or []),
            }
        )

    return {
        "schema": "tracka_logic_weights_shadow_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_to_track_a_shadow",
        "non_gating": True,
        "research_only": True,
        "track_wall": {
            "track_a_bridge": False,
            "live_trading_bridge": False,
            "policy_mutation_forbidden": True,
            "theology_to_output_forbidden": True,
        },
        "inputs": {
            "path_gate": str(path_gate.relative_to(ROOT)).replace("\\", "/") if path_gate.is_relative_to(ROOT) else str(path_gate),
            "verse_shadow": str(shadow_path.relative_to(ROOT)).replace("\\", "/")
            if shadow_path.is_relative_to(ROOT)
            else str(shadow_path),
            "psi_logic": str(psi_path.relative_to(ROOT)).replace("\\", "/") if psi_path.is_relative_to(ROOT) else str(psi_path),
            "max_terms": int(max_terms),
        },
        "summary": {
            "term_pool_size": len(term_counter),
            "selected_terms": len(weighted_terms),
        },
        "weighted_terms": weighted_terms,
        "must_keep_terms_shadow": [w["term"] for w in weighted_terms],
        "reproduce": "py scripts/extract_logic_weights_for_track_a_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-terms", type=int, default=48)
    ap.add_argument("--path-gate", type=Path, default=PATH_GATE_DEFAULT)
    ap.add_argument("--shadow", type=Path, default=SHADOW_DEFAULT)
    ap.add_argument("--psi", type=Path, default=PSI_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    doc = build(
        max_terms=max(8, int(args.max_terms)),
        path_gate=args.path_gate,
        shadow_path=args.shadow,
        psi_path=args.psi,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = int((doc.get("summary") or {}).get("selected_terms") or 0) > 0
    print(json.dumps({"ok": ok, "selected_terms": doc["summary"]["selected_terms"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
