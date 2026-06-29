#!/usr/bin/env python3
"""Verify Job 38:4 scope-reset anchor + theme_39 alignment ([HYPO]).

Reproducible:
  py scripts/verify_logos_job_scope_reset_v1.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CORPUS = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
TOPOLOGY = ROOT / "docs/final/artifacts/logos_topology_sidecar_job_suffering_reason_v1_latest.json"
THEME = ROOT / "docs/research/logos_metaphor_db_v1/theme_39_job_suffering.json"
OUT = ROOT / "reports/logos_job_scope_reset_verify_v1_latest.json"

VERSE_384 = "Job.38.4"
VERSE_18 = "Job.1.8"
VERSE_23 = "Job.2.3"

SCOPE_LEMMAS = (
    {
        "lemma": "איפה",
        "pattern": re.compile(r"א.?פ.?ה"),
        "role_ko": "where-질문 — why(למה) 프레임 아님",
    },
    {
        "lemma": "יסד",
        "pattern": re.compile(r"י.?ס.?ד"),
        "role_ko": "foundation — 창조 기초·scope 경계",
    },
    {
        "lemma": "בינה",
        "pattern": re.compile(r"ב.?י.?נ.?ה"),
        "role_ko": "understanding — 인간 앎의 한계",
    },
)

BLAMELESS_LEMMAS = (
    {
        "lemma": "תם",
        "pattern": re.compile(r"ת.?ם"),
        "role_ko": "tam — 순전(blameless) theme_39 병렬",
    },
    {
        "lemma": "ישר",
        "pattern": re.compile(r"י.?ש.?ר"),
        "role_ko": "yashar — 정직",
    },
)

WHY_PATTERN = re.compile(r"ל.?מ.?ה")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strip_marks(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _load_verse_row(jsonl: Path, verse_id: str) -> dict[str, Any] | None:
    if not jsonl.is_file():
        return None
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if str(row.get("verse_id") or "") == verse_id:
                return row
    return None


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check_lemmas(
    *,
    row: dict[str, Any] | None,
    verse_ref: str,
    checks: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    original = str((row or {}).get("original_text") or (row or {}).get("text") or "")
    stripped = _strip_marks(original)
    for check in checks:
        rows.append(
            {
                "lemma": check["lemma"],
                "verse_ref": verse_ref,
                "corpus_present": bool(check["pattern"].search(stripped)),
                "role_ko": check["role_ko"],
            }
        )
    return rows


def verify(*, corpus: Path, topology_path: Path, theme_path: Path) -> dict[str, Any]:
    errors: list[str] = []

    row384 = _load_verse_row(corpus, VERSE_384)
    row18 = _load_verse_row(corpus, VERSE_18)
    row23 = _load_verse_row(corpus, VERSE_23)

    if not row384:
        errors.append(f"missing corpus row: {VERSE_384}")
    if not row18:
        errors.append(f"missing corpus row: {VERSE_18}")
    if not row23:
        errors.append(f"missing corpus row: {VERSE_23}")

    scope_lemmas = _check_lemmas(row=row384, verse_ref=VERSE_384, checks=SCOPE_LEMMAS)
    blameless_18 = _check_lemmas(row=row18, verse_ref=VERSE_18, checks=BLAMELESS_LEMMAS)
    blameless_23 = _check_lemmas(row=row23, verse_ref=VERSE_23, checks=BLAMELESS_LEMMAS)

    for row in scope_lemmas + blameless_18 + blameless_23:
        if not row["corpus_present"]:
            errors.append(f"lemma {row['lemma']} missing in {row['verse_ref']}")

    why_in_384 = False
    if row384:
        stripped384 = _strip_marks(str(row384.get("original_text") or row384.get("text") or ""))
        why_in_384 = bool(WHY_PATTERN.search(stripped384))

    theme = _load_json(theme_path)
    theme_node = next(
        (n for n in theme.get("semantic_nodes") or [] if n.get("node_id") == "NODE_JOB_38_4"),
        None,
    )
    theme_ok = theme_node is not None and "38:4" in str(theme_node.get("ref") or "")

    topology = _load_json(topology_path)
    packs = ((topology.get("topology") or {}).get("reading_pack") or [])
    pack2 = next((p for p in packs if p.get("pack_id") == "scope_reset_no_why"), None)
    pack2_md = (pack2 or {}).get("deep_synthesis_md_path")
    pack2_md_ok = bool(pack2_md and (ROOT / str(pack2_md)).is_file())

    gap = ((topology.get("topology") or {}).get("intentional_causal_gap") or {})
    why_assembled = gap.get("why_question_assembled")

    if why_assembled is not False:
        errors.append("why_question_assembled must be false")
    if not theme_ok:
        errors.append("theme_39 NODE_JOB_38_4 missing")
    if not pack2_md_ok:
        errors.append("pack2 deep_synthesis_md_path missing or file not found")

    return {
        "schema": "logos_job_scope_reset_verify_v1",
        "generated_at_utc": _utc(),
        "ok": not errors,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "why_question_assembled": False,
        "query_id": "job_suffering_reason",
        "pack_id": "scope_reset_no_why",
        "anchor_verse": {
            "verse_ref": VERSE_384,
            "original_text_bhs": (row384 or {}).get("original_text"),
            "text_plain": (row384 or {}).get("text"),
            "why_lemma_lamah_present": why_in_384,
            "scope_not_why_ko": "38:4에 למה(why) surface 없음 — איפה/יסד/בינה scope 질문 [corpus floor]",
        },
        "scope_lemma_verification": scope_lemmas,
        "blameless_outage_parallel": {
            "theme_39_path": theme_path.relative_to(ROOT).as_posix(),
            "theme_39_node_job_38_4": theme_node,
            "governance_mapping": theme.get("governance_mapping"),
            "Job.1.8": blameless_18,
            "Job.2.3": blameless_23,
        },
        "pack1_bridge_junction_ko": (
            "Pack2 scope reset(38:4) → Pack1 Bridge(42:5–6) — why 답 없이 질문 유형·관계 피벗 [HYPO]"
        ),
        "topology_pack2": {
            "pack_id": (pack2 or {}).get("pack_id"),
            "deep_synthesis_md_path": pack2_md,
        },
        "interpretive_boundary_ko": (
            "scope lemma 존재·why surface 부재 ≠ 38–41 해석 확정. theme_39는 ops 은유·NON_GATING."
        ),
        "errors": errors,
        "reproducible_command": "py scripts/verify_logos_job_scope_reset_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--topology", type=Path, default=TOPOLOGY)
    ap.add_argument("--theme", type=Path, default=THEME)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    report = verify(
        corpus=args.corpus if args.corpus.is_absolute() else ROOT / args.corpus,
        topology_path=args.topology if args.topology.is_absolute() else ROOT / args.topology,
        theme_path=args.theme if args.theme.is_absolute() else ROOT / args.theme,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  ok={report['ok']} why_in_38:4={report['anchor_verse']['why_lemma_lamah_present']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
