#!/usr/bin/env python3
"""Emit prophecy Track A candidate pre-review artifact from separated signoff packet."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_IN = ART / "btrack_promotion_signoff_packet_separated_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_track_a_candidate_pre_review_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src = _read_json(args.signoff_json)
    t = ((src.get("track_status") or {}).get("prophecy") or {})
    decision = str(t.get("decision") or "HOLD")
    blockers = t.get("blockers") if isinstance(t.get("blockers"), list) else []
    next_actions = t.get("next_actions_ko") if isinstance(t.get("next_actions_ko"), list) else []

    status = "PRE_REVIEW_CANDIDATE" if decision == "READY_FOR_HUMAN_SIGNOFF" else "HOLD"
    out = {
        "schema": "track_a_candidate_pre_review_v1",
        "generated_at_utc": _now(),
        "track": "prophecy",
        "research_only": True,
        "status": status,
        "decision_snapshot": decision,
        "blockers": blockers,
        "next_actions_ko": next_actions,
        "inputs": {
            "signoff_json": str(args.signoff_json).replace("\\", "/"),
            "promotion_gate": "docs/final/artifacts/prophecy_promotion_gates_v1_panel_calibrated_latest.json",
        },
        "notes_ko": [
            "auto_promote_ready=true여도 human sign-off 없이 A-track/live 자동 승격 금지",
            "본 파일은 인사이더 프리리뷰 큐 표기용이다",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out).replace("\\", "/"))
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
