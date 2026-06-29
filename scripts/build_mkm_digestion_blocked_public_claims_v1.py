#!/usr/bin/env python3
"""Aggregate digestion-blocked external numerics for investor Fact-Lock appendix (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_digestion_blocked_public_claims_latest.json"

DEFAULT_SOURCES = (
    ROOT / "docs/final/artifacts/tier0_hybrid_ai_web_sweep_2026-06-20_digested_facts_latest.json",
    ROOT / "docs/final/artifacts/universal_root_lexicon_matrix_gemini_report_2026-06-21_digested_facts_latest.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _row_from_fact(fact: dict[str, Any], *, source_path: str) -> dict[str, Any]:
    verification = fact.get("verification") or {}
    prov = fact.get("provenance") or {}
    status = str(verification.get("status") or "Unknown")
    disposition = "blocked_public"
    if status == "Right":
        disposition = "external_cite_ok_abstract_only"
    elif status == "Unknown":
        disposition = "blocked_public_no_verification"
    return {
        "fact_id": fact.get("fact_id"),
        "value": fact.get("value"),
        "unit": fact.get("unit"),
        "comparison_arm": fact.get("comparison_arm"),
        "verification_status": status,
        "verification_method": verification.get("method"),
        "arxiv_id": prov.get("arxiv_id"),
        "disposition": disposition,
        "source_digested_path": source_path,
    }


def build_blocked_claims(
    *,
    digested_paths: list[Path],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in digested_paths:
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        rel = _posix(path)
        for fact in doc.get("facts") or []:
            prov = fact.get("provenance") or {}
            status = str((fact.get("verification") or {}).get("status") or "Unknown")
            if status == "Right" and (fact.get("mkm_wiring") or {}).get("wired"):
                continue
            if status == "Right" and prov.get("arxiv_id"):
                rows.append(_row_from_fact(fact, source_path=rel))
                continue
            if status in {"Wrong", "Unknown"}:
                rows.append(_row_from_fact(fact, source_path=rel))

    wrong = [r for r in rows if r["verification_status"] == "Wrong"]
    unknown = [r for r in rows if r["verification_status"] == "Unknown"]
    external_ok = [r for r in rows if r["disposition"] == "external_cite_ok_abstract_only"]

    return {
        "schema": "mkm_digestion_blocked_public_claims_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "policy": "Wrong/Unknown external numerics must not appear in investor deck hero or PUBLIC_FACING copy",
        "wrong_count": len(wrong),
        "unknown_count": len(unknown),
        "external_abstract_ok_count": len(external_ok),
        "blocked_rows": rows,
        "wrong_rows": wrong,
        "unknown_rows": unknown,
        "reproduce": "py scripts/build_mkm_digestion_blocked_public_claims_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build digestion-blocked public claims artifact")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--digested",
        type=Path,
        action="append",
        default=None,
        help="Digested facts JSON (repeatable; default: hybrid tier0 + gemini raw)",
    )
    args = parser.parse_args()

    paths = [p.resolve() for p in (args.digested or list(DEFAULT_SOURCES))]
    doc = build_blocked_claims(digested_paths=paths)
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out_path": _posix(out),
                "wrong_count": doc["wrong_count"],
                "unknown_count": doc["unknown_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
