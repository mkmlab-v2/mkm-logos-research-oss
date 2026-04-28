#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
SCORECARD_DEFAULT = ART / "pointerguard_two_tier_perf_scorecard_latest.json"
OUT_DEFAULT = ART / "a_codeai_fact_lock_public_copy_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--scorecard-json", type=Path, default=SCORECARD_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    scorecard_path = args.scorecard_json if args.scorecard_json.is_absolute() else ROOT / args.scorecard_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    readiness = _read_json(readiness_path) if readiness_path.exists() else {}
    scorecard = _read_json(scorecard_path) if scorecard_path.exists() else {}
    readiness_all_ok = bool(readiness.get("all_ok", False))
    executive_read = str(scorecard.get("executive_read", {}).get("decision", "CONTROLLED_BETA_ONLY"))

    hero = "PointerGuard Router (Controlled Beta)"
    subtitle = "Condition-based token/input compression with automatic fallback and operational guardrails."
    status_line = (
        "Current status: readiness=green, controlled beta recommended."
        if readiness_all_ok
        else "Current status: readiness gate is not green; public claims are restricted."
    )

    bullets = [
        "This service is promoted with measured evidence only (Fact-Lock).",
        "When guard conditions are unmet, traffic is downgraded to safe fallback mode automatically.",
        "Public benchmark uses synthetic/anonymized input scope only.",
        "No guarantee of universal uplift outside validated operating conditions.",
    ]

    claims = [
        {
            "title": "What we claim",
            "items": [
                "Conditional cost and latency improvement in validated operating zones.",
                "Automatic safety fallback (HOLD/track_a_primary) when readiness or health checks fail.",
                "Operational transparency via timestamped benchmark and readiness artifacts.",
            ],
        },
        {
            "title": "What we do not claim",
            "items": [
                "No unconditional global performance guarantee.",
                "No claim that all workloads receive equal benefit.",
                "No exposure of private corpora, secrets, or internal codebook internals.",
            ],
        },
    ]

    cta = {
        "label": "Request Controlled Beta",
        "note": "Pilot onboarding is limited to scoped B2B workloads with monitoring and guardrail acceptance.",
    }

    out_doc = {
        "schema": "a_codeai_fact_lock_public_copy_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "readiness_json": str(readiness_path),
            "scorecard_json": str(scorecard_path),
        },
        "status": {
            "readiness_all_ok": readiness_all_ok,
            "executive_read_decision": executive_read,
        },
        "copy": {
            "hero": hero,
            "subtitle": subtitle,
            "status_line": status_line,
            "bullets": bullets,
            "claims": claims,
            "cta": cta,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "readiness_all_ok": readiness_all_ok}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
