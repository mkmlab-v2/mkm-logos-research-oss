#!/usr/bin/env python3
"""Wire HAAN paper-digest pointers to SASANG analogy_bench contract (sidecar only).

Does NOT modify SASANG_CROSS_REF_DRAFT.json entries (chunk-table CI contract).
research_only · send_gate HOLD
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POINTERS = ROOT / "docs/final/artifacts/haan_sasang_paper_crossref_pointers_v1_latest.json"
SASANG_CROSS_REF = ROOT / "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/haan_sasang_analogy_bench_wire_v1_latest.json"

_LINK_MAP = {
    "paper_digest_pointer": "analogy_bench",
    "cross_lens_logos_ijeoma": "analogy_bench",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def build_wire(*, pointers_path: Path) -> dict[str, Any]:
    pointers_doc = json.loads(pointers_path.read_text(encoding="utf-8"))
    sasang_anchor = _rel(SASANG_CROSS_REF) if SASANG_CROSS_REF.is_file() else None
    wires: list[dict[str, Any]] = []
    for i, ptr in enumerate(pointers_doc.get("pointers") or [], start=1):
        link_in = str(ptr.get("link_type") or "paper_digest_pointer")
        wires.append(
            {
                "wire_id": f"HAAN_WIRE_{i:02d}",
                "tier0": ptr.get("tier0"),
                "title_guess": ptr.get("title_guess"),
                "source_link_type": link_in,
                "wire_link_type": _LINK_MAP.get(link_in, "analogy_bench"),
                "sasang_cross_ref_anchor": sasang_anchor,
                "corpus_type": "haan_paper_digest_tier0",
                "confidence": 0.15,
                "rationale": "[HYPO] HAAN library paper Tier0 → SASANG bench sidecar; "
                "no chunk_id; no prescription; no Track A merge.",
                "note": ptr.get("note") or "SASANG_CROSS_REF_DRAFT 본문 수정 없음",
                "forbidden": [
                    "clinical_cohort_label_substitution",
                    "prescription_engine_trigger",
                    "track_a_autotrigger",
                    "false_equivalence_16_state",
                ],
            }
        )
    return {
        "schema": "haan_sasang_analogy_bench_wire_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "disclaimer": "Sidecar wire only — SASANG_CROSS_REF_DRAFT entries unchanged.",
        "pointer_source": _rel(pointers_path),
        "sasang_cross_ref_readonly": sasang_anchor,
        "wire_count": len(wires),
        "wires": wires,
        "reproduce": "py scripts/build_haan_sasang_analogy_bench_wire_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pointers", type=Path, default=POINTERS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.pointers.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.pointers}"}, ensure_ascii=False))
        return 2
    doc = build_wire(pointers_path=args.pointers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "wire_count": doc["wire_count"], "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
