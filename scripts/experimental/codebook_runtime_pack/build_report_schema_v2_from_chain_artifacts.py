#!/usr/bin/env python3
"""Materialize report_schema_v2_latest.json from existing monthly / scoreboard artifacts (no LLM)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROPHECY = ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
DEFAULT_SCOREBOARD = ROOT / "docs" / "final" / "artifacts" / "insight_effectiveness_scoreboard_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "report_schema_v2_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
        return o if isinstance(o, dict) else {}
    except Exception:
        return {}


def _claim(cid: str, text: str, label: str, grounded: bool, evidence_ref: str) -> dict[str, Any]:
    return {
        "id": cid,
        "text": text,
        "label": label,
        "grounded": grounded,
        "evidence_ref": evidence_ref,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prophecy", type=Path, default=DEFAULT_PROPHECY)
    ap.add_argument("--scoreboard", type=Path, default=DEFAULT_SCOREBOARD)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    prophecy = _load(args.prophecy)
    scoreboard = _load(args.scoreboard)
    if not prophecy and not scoreboard:
        raise SystemExit(f"need at least one input: {args.prophecy} or {args.scoreboard}")

    claims: list[dict[str, Any]] = []
    meta = prophecy.get("meta") if isinstance(prophecy.get("meta"), dict) else {}
    risk = prophecy.get("risk_profile") if isinstance(prophecy.get("risk_profile"), dict) else {}

    if meta:
        cd = str(meta.get("core_decision") or "")
        cs = meta.get("core_score")
        gr = str(meta.get("gate_reason") or "")
        if cd:
            claims.append(
                _claim(
                    "chain_prophecy_core_decision",
                    f"Monthly prophecy meta reports core_decision={cd}.",
                    "FACT",
                    True,
                    str(args.prophecy),
                )
            )
        if cs is not None:
            claims.append(
                _claim(
                    "chain_prophecy_core_score",
                    f"Monthly prophecy meta reports core_score={cs}.",
                    "FACT",
                    True,
                    str(args.prophecy),
                )
            )
        if gr:
            claims.append(
                _claim(
                    "chain_prophecy_gate_reason",
                    f"Monthly prophecy meta lists gate_reason={gr}.",
                    "FACT",
                    True,
                    str(args.prophecy),
                )
            )
    if risk:
        mode = str(risk.get("mode") or "")
        if mode:
            claims.append(
                _claim(
                    "chain_risk_mode",
                    f"Risk profile mode is {mode}.",
                    "FACT",
                    True,
                    str(args.prophecy),
                )
            )

    if scoreboard:
        pr = scoreboard.get("is_promotion_ready")
        claims.append(
            _claim(
                "chain_insight_promotion_ready",
                f"Insight scoreboard is_promotion_ready={pr}.",
                "FACT",
                True,
                str(args.scoreboard),
            )
        )
        st = str(scoreboard.get("promotion_status") or "")
        if st:
            claims.append(
                _claim(
                    "chain_insight_promotion_status",
                    f"Insight scoreboard promotion_status={st}.",
                    "FACT",
                    True,
                    str(args.scoreboard),
                )
            )

    if not claims:
        raise SystemExit("no claims derived from inputs (unexpected empty meta/scoreboard)")

    doc = {
        "schema": "report_schema_v2_from_chain_artifacts_v1",
        "generated_at_utc": _utc_now(),
        "sources": {
            "prophecy_monthly": str(args.prophecy) if prophecy else None,
            "insight_scoreboard": str(args.scoreboard) if scoreboard else None,
        },
        "claims": claims,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
