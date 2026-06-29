#!/usr/bin/env python3
"""Verify Job 1:6 heavenly council literal frame + permission bounds ([HYPO]).

Reproducible:
  py scripts/verify_logos_job_literal_council_v1.py
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
OUT = ROOT / "reports/logos_job_literal_council_verify_v1_latest.json"

VERSE_16 = "Job.1.6"
VERSE_112 = "Job.1.12"
VERSE_26 = "Job.2.6"

COUNCIL_16 = (
    {
        "lemma": "בני",
        "pattern": re.compile(r"ב.?נ"),
        "role_ko": "bene — sons (בני האלהים)",
    },
    {
        "lemma": "אלהים",
        "pattern": re.compile(r"א.?ל.?ה.?י.?ם"),
        "role_ko": "elohim — divine council attendance",
    },
    {
        "lemma": "התיצב",
        "pattern": re.compile(r"י.?צ.?ב"),
        "role_ko": "hityatsav — stand before YHWH",
    },
    {
        "lemma": "שטן",
        "pattern": re.compile(r"ש.?ט.?ן"),
        "role_ko": "satan — ha- definite adversary role",
    },
)

PERMISSION_112 = (
    {
        "lemma": "בידך",
        "pattern": re.compile(r"י.?ד"),
        "role_ko": "b'yadekha — in your hand (scope handoff)",
    },
    {
        "lemma": "אל תשלח",
        "pattern": re.compile(r"א.?ל.*(ש.?ל.?ח|ת.?ש.?ל.?ח)"),
        "role_ko": "al tishlach — do not stretch hand (bound on Job)",
    },
)

PERMISSION_26 = (
    {
        "lemma": "נפש",
        "pattern": re.compile(r"נ.?פ.?ש"),
        "role_ko": "nefesh — life boundary",
    },
    {
        "lemma": "שמר",
        "pattern": re.compile(r"ש.?מ.?ר"),
        "role_ko": "shmor — preserve (life cap)",
    },
)

MISWIRE_FORBIDDEN = (
    "dual_god_satan_entity_confirmed",
    "track_a_command_metaphor_promotion",
    "why_causality_assembled",
    "pack1_topology_auto_merge",
)


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


def verify(*, corpus: Path, topology_path: Path) -> dict[str, Any]:
    errors: list[str] = []

    row16 = _load_verse_row(corpus, VERSE_16)
    row112 = _load_verse_row(corpus, VERSE_112)
    row26 = _load_verse_row(corpus, VERSE_26)

    if not row16:
        errors.append(f"missing corpus row: {VERSE_16}")
    if not row112:
        errors.append(f"missing corpus row: {VERSE_112}")
    if not row26:
        errors.append(f"missing corpus row: {VERSE_26}")

    council = _check_lemmas(row=row16, verse_ref=VERSE_16, checks=COUNCIL_16)
    perm112 = _check_lemmas(row=row112, verse_ref=VERSE_112, checks=PERMISSION_112)
    perm26 = _check_lemmas(row=row26, verse_ref=VERSE_26, checks=PERMISSION_26)

    for row in council + perm112 + perm26:
        if not row["corpus_present"]:
            errors.append(f"lemma {row['lemma']} missing in {row['verse_ref']}")

    topology = _load_json(topology_path)
    topo = topology.get("topology") or {}
    anchor = str(topology.get("anchor_ref") or topo.get("anchor_ref") or "")
    if anchor != VERSE_16:
        errors.append(f"anchor_ref must be {VERSE_16}, got {anchor!r}")

    packs = topo.get("reading_pack") or []
    pack3 = next((p for p in packs if p.get("pack_id") == "literal_council_only"), None)
    pack3_md = (pack3 or {}).get("deep_synthesis_md_path")
    if not pack3_md or not (ROOT / str(pack3_md)).is_file():
        errors.append("pack3 deep_synthesis_md_path missing or file not found")

    gap = topo.get("intentional_causal_gap") or {}
    if gap.get("why_question_assembled") is not False:
        errors.append("why_question_assembled must be false")

    ha_satan = False
    if row16:
        stripped16 = _strip_marks(str(row16.get("original_text") or row16.get("text") or ""))
        ha_satan = bool(re.search(r"ה.?ש.?ט.?ן", stripped16))

    return {
        "schema": "logos_job_literal_council_verify_v1",
        "generated_at_utc": _utc(),
        "ok": not errors,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "why_question_assembled": False,
        "query_id": "job_suffering_reason",
        "pack_id": "literal_council_only",
        "anchor_ref": VERSE_16,
        "council_verse": {
            "verse_ref": VERSE_16,
            "original_text_bhs": (row16 or {}).get("original_text"),
            "text_plain": (row16 or {}).get("text"),
            "ha_satan_definite_article": ha_satan,
            "lemma_verification": council,
        },
        "permission_bounds": {
            VERSE_112: {
                "original_text_bhs": (row112 or {}).get("original_text"),
                "lemma_verification": perm112,
            },
            VERSE_26: {
                "original_text_bhs": (row26 or {}).get("original_text"),
                "lemma_verification": perm26,
            },
        },
        "miswire_guards": {
            "forbidden_promotions": list(MISWIRE_FORBIDDEN),
            "pack_isolation_ko": "Pack3=council literal only; Pack1/2 병렬·NON_GATING·자동 합선 금지",
        },
        "topology_pack3": {
            "pack_id": (pack3 or {}).get("pack_id"),
            "deep_synthesis_md_path": pack3_md,
        },
        "interpretive_boundary_ko": (
            "corpus·허가·상한 확인 ≠ bene ha-elohim 정체 확정·이원신·Track A 트리거."
        ),
        "errors": errors,
        "reproducible_command": "py scripts/verify_logos_job_literal_council_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--topology", type=Path, default=TOPOLOGY)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    report = verify(
        corpus=args.corpus if args.corpus.is_absolute() else ROOT / args.corpus,
        topology_path=args.topology if args.topology.is_absolute() else ROOT / args.topology,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"  ok={report['ok']} anchor={report['anchor_ref']} ha_satan={report['council_verse']['ha_satan_definite_article']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
