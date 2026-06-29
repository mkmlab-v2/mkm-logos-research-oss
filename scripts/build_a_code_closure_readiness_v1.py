#!/usr/bin/env python3
"""A-code RQ-028/029/031 closure readiness ([HYPO] · does not set RESEARCH CLOSED)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "reports/a_code_rq_close_gate_v1_latest.json"
DEFAULT_ARCHIVE = ROOT / "reports/a_code_governor_signoff_archive_pack_v1_latest.json"
DEFAULT_CLOSE = ROOT / "docs/final/artifacts/a_code_commander_close_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/a_code_closure_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    gate = _read(DEFAULT_GATE)
    archive = _read(DEFAULT_ARCHIVE)
    close_doc = _read(DEFAULT_CLOSE)

    gate_summary = gate.get("summary") or {}
    mechanical_ok = gate_summary.get("mechanical_close_candidate") is True
    archive_ok = archive.get("archive_ready") is True
    close_ok = (
        close_doc.get("rq_028_closed") is True
        and close_doc.get("rq_029_closed") is True
        and close_doc.get("rq_031_closed") is True
    )

    checks = [
        {
            "check": "rq_close_gate_mechanical",
            "path": str(DEFAULT_GATE.relative_to(ROOT)).replace("\\", "/"),
            "ok": mechanical_ok,
            "detail": gate_summary.get("decision"),
        },
        {
            "check": "signoff_archive_ready",
            "path": str(DEFAULT_ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "ok": archive_ok,
            "detail": archive.get("archive_ready"),
        },
        {
            "check": "commander_close_artifact",
            "path": str(DEFAULT_CLOSE.relative_to(ROOT)).replace("\\", "/"),
            "ok": close_ok,
            "detail": close_doc.get("close_reference") if close_ok else None,
        },
    ]

    mechanics_bundle_ok = mechanical_ok and archive_ok
    closure_allowed = mechanics_bundle_ok and close_ok

    blockers: list[str] = []
    if not mechanical_ok:
        blockers.append("RQ close gate mechanical_close_candidate=false")
    if not archive_ok:
        blockers.append("sign-off archive pack archive_ready=false")
    if not close_ok:
        blockers.insert(
            0,
            "commander close artifact missing — run record_a_code_rq_commander_close_v1.py with MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED=1",
        )

    return {
        "schema": "a_code_closure_readiness_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "rq_ids": ["RQ-028", "RQ-029", "RQ-031"],
        "hypothesis_tier": "B",
        "research_only": True,
        "mechanics_bundle_ok": mechanics_bundle_ok,
        "closure_allowed": closure_allowed,
        "checks": checks,
        "blockers_ko": blockers,
        "next_human_gate": (
            ["RESEARCH_OPEN_QUESTIONS_V1.md 수동 CLOSED 갱신 (에이전트 금지)"]
            if closure_allowed
            else [
                "MKM_ACODE_RQ_CLOSE_HUMAN_APPROVED=1 설정 후 record_a_code_rq_commander_close_v1.py",
                "RESEARCH_OPEN_QUESTIONS_V1.md 수동 CLOSED 갱신",
            ]
        ),
        "verdict_ko": (
            "A-code RQ CLOSED 이관 OK — commander close 기록됨."
            if closure_allowed
            else (
                "기계적 번들 OK — commander close 대기."
                if mechanics_bundle_ok
                else "기계적 번들 미충족 — smoke/archive/gate 재실행."
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: {args.out} mechanics_bundle_ok={doc.get('mechanics_bundle_ok')} "
        f"closure_allowed={doc.get('closure_allowed')}"
    )
    if args.strict and not doc.get("mechanics_bundle_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
