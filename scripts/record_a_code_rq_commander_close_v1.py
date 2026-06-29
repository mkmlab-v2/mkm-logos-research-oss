#!/usr/bin/env python3
"""Record commander CLOSED for RQ-028/029/031 (human gate · B-track archive)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "reports/a_code_rq_close_gate_v1_latest.json"
DEFAULT_ARCHIVE = ROOT / "reports/a_code_governor_signoff_archive_pack_v1_latest.json"
DEFAULT_CHECKLIST = ROOT / "reports/a_code_rq_close_human_checklist_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/a_code_commander_close_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    if p.is_relative_to(ROOT):
        return str(p.relative_to(ROOT)).replace("\\", "/")
    return str(p).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _human_close_approved() -> bool:
    raw = os.getenv("MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def build(
    *,
    close_reference: str,
    note: str = "",
    gate_path: Path | None = None,
    archive_path: Path | None = None,
) -> dict[str, Any]:
    if not _human_close_approved():
        raise ValueError(
            "MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED must be truthy (commander human gate)"
        )

    gate = _load(gate_path or DEFAULT_GATE)
    summary = gate.get("summary") or {}
    if summary.get("mechanical_close_candidate") is not True:
        raise ValueError("mechanical_close_candidate is false; run close gate bundle first")

    archive = _load(archive_path or DEFAULT_ARCHIVE)
    if archive.get("archive_ready") is not True:
        raise ValueError("archive_ready is false; run sign-off archive bundle first")

    ref = close_reference.strip()
    if not ref:
        raise ValueError("close_reference required")

    return {
        "schema": "a_code_commander_close_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "classification": "INTERNAL_ONLY",
        "rq_ids": ["RQ-028", "RQ-029", "RQ-031"],
        "rq_028_closed": True,
        "rq_029_closed": True,
        "rq_031_closed": True,
        "rq_status": "CLOSED",
        "hypothesis_tier": "B",
        "research_only": True,
        "closed_at_utc": _utc(),
        "closed_by": "commander",
        "close_reference": ref,
        "commander_note": note.strip() or "commander close after A-code operator-assist lane archive",
        "evidence_pointers": {
            "rq_close_gate": _rel(DEFAULT_GATE),
            "signoff_archive_pack": _rel(DEFAULT_ARCHIVE),
            "human_checklist": _rel(DEFAULT_CHECKLIST) if DEFAULT_CHECKLIST.is_file() else None,
            "constitution_section": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §1.2.2",
            "namespace": _rel(ROOT / "experiments/a_code_12ai_v2"),
        },
        "explicit_not_promoted": [
            "Track A compression ACTIVE report or MS paste KPI",
            "live trading triggers or ECC materialization",
            "CONSTITUTION body edit without separate PR",
            "price directional hit rate as A-code governor proof",
            "jaccard/saving bridge merge from B-track",
            "clinical or patient_care_bundle gating",
        ],
        "manual_remainder_ko": [
            "docs/research/RESEARCH_OPEN_QUESTIONS_V1.md 에 RQ-028/029/031 CLOSED 행 수동 갱신",
            "에이전트가 RESEARCH CLOSED 자동 편집하지 않음",
        ],
        "boundary_ack": (
            "RQ-028/029/031 CLOSED = A-code B-track operator-assist sandbox phase archived. "
            "experiments/a_code_12ai_v2/ remains [HYPO]·research_only. "
            "No Track A·live·MS promotion implied."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--close-reference",
        default="COMMANDER-ACODE-RQ-CLOSE-2026-06-05",
        help="human gate reference id",
    )
    parser.add_argument("--note", default="")
    parser.add_argument("--gate-path", type=Path, default=None)
    parser.add_argument("--archive-path", type=Path, default=None)
    args = parser.parse_args()

    doc = build(
        close_reference=args.close_reference,
        note=args.note,
        gate_path=args.gate_path,
        archive_path=args.archive_path,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": _rel(args.out), "rq_status": "CLOSED", "rq_ids": doc["rq_ids"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
