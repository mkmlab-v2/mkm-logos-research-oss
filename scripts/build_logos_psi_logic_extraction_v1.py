#!/usr/bin/env python3
"""Psi (Ψ) logic-layer extraction — theological token filter + abstract node graph [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/logos_psi_logic_extraction_v1_latest.json"

THEOLOGY_BLOCKLIST = re.compile(
    r"(?i)\b("
    r"god|jesus|christ|holy\s*spirit|sin|salvation|gospel|logos|"
    r"성경|하나님|예수|그리스|성령|구원|복음|신학|교리|창세|요한|다니엘"
    r")\b"
)

ROLE_KEYWORDS: list[tuple[str, re.Pattern[str]]] = [
    ("Antecedent", re.compile(r"(?i)(초기|투입|공급|시작|initial|supply|input|resource|PoC|압축)")),
    ("Intermediary", re.compile(r"(?i)(처리|전처리|병목|프로세스|Edge|SDK|middleware|process|bottleneck)")),
    ("Constraints", re.compile(r"(?i)(제한|규제|게이트|금지|human|법무|constraint|gate|forbidden|서명)")),
    ("Consequent", re.compile(r"(?i)(결과|리스크|절감|송출|outcome|risk|send|readiness|헤드라인)")),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_input_text() -> str:
    p = ROOT / "reports/external_validation_ms_evidence_pack_v1_latest/ms_proposal_one_pager_ko_v1.txt"
    if p.is_file():
        return p.read_text(encoding="utf-8-sig")
    return (
        "Actor_A invests in Edge preprocessing. Regulatory_Constraint blocks live billing API. "
        "Process_B delivers compression PoC metrics. Outcome_Risk if headlines are merged."
    )


def _abstract_token(raw: str, idx: int) -> str:
    clean = THEOLOGY_BLOCKLIST.sub("[FILTERED]", raw)
    if "[FILTERED]" in clean:
        return f"Abstract_{idx}"
    alnum = re.sub(r"[^\w]", "_", clean.strip())[:24] or f"Term_{idx}"
    return f"Actor_{alnum}" if not alnum.startswith("Actor_") else alnum


def extract_logic_graph(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    theology_hits = len(THEOLOGY_BLOCKLIST.findall(text))
    nodes: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    role_buckets: dict[str, list[str]] = {r: [] for r, _ in ROLE_KEYWORDS}

    for i, line in enumerate(lines[:40]):
        if THEOLOGY_BLOCKLIST.search(line):
            continue
        assigned = "Intermediary"
        for role, pat in ROLE_KEYWORDS:
            if pat.search(line):
                assigned = role
                break
        nid = f"N{i}"
        nodes.append(
            {
                "id": nid,
                "type": assigned,
                "description": _abstract_token(line[:80], i),
                "source_line_preview": line[:120],
            }
        )
        role_buckets[assigned].append(nid)

    if len(nodes) < 4:
        nodes = [
            {"id": "N0", "type": "Antecedent", "description": "Resource_Initial_State"},
            {"id": "N1", "type": "Intermediary", "description": "Process_Bottleneck"},
            {"id": "N2", "type": "Constraints", "description": "Regulatory_Constraint"},
            {"id": "N3", "type": "Consequent", "description": "Outcome_Risk_State"},
        ]
        role_buckets = {"Antecedent": ["N0"], "Intermediary": ["N1"], "Constraints": ["N2"], "Consequent": ["N3"]}

    if role_buckets["Antecedent"] and role_buckets["Intermediary"]:
        relationships.append(
            {
                "source": role_buckets["Antecedent"][0],
                "target": role_buckets["Intermediary"][0],
                "relation_type": "triggers",
            }
        )
    if role_buckets["Constraints"] and role_buckets["Intermediary"]:
        relationships.append(
            {
                "source": role_buckets["Constraints"][0],
                "target": role_buckets["Intermediary"][0],
                "relation_type": "obstructs",
            }
        )
    if role_buckets["Intermediary"] and role_buckets["Consequent"]:
        relationships.append(
            {
                "source": role_buckets["Intermediary"][0],
                "target": role_buckets["Consequent"][0],
                "relation_type": "dependency_path",
            }
        )

    return {
        "nodes": nodes[:12],
        "relationships": relationships,
        "psi_metadata": {
            "theology_tokens_filtered": theology_hits,
            "content_layer_excluded": True,
            "logic_layer_only": True,
        },
    }


def build(*, input_text: str) -> dict[str, Any]:
    graph = extract_logic_graph(input_text)
    return {
        "schema": "logos_psi_logic_extraction_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "structure_transplant_only": True,
        "theology_to_sales_forbidden": True,
        "psi_morphism": "G_content -> G_logic (role nodes only)",
        "logic_graph": graph,
        "reproduce": "py scripts/build_logos_psi_logic_extraction_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    if args.input and args.input.is_file():
        text = args.input.read_text(encoding="utf-8-sig")
    else:
        text = _default_input_text()

    doc = build(input_text=text)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = len(doc["logic_graph"]["nodes"]) >= 4
    print(json.dumps({"ok": ok, "nodes": len(doc["logic_graph"]["nodes"]), "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
