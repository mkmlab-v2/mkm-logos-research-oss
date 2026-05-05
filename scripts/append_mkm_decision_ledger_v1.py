#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Append MKM decision ledger row from latest artifacts.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument("--actor", default="athena-agent")
    ap.add_argument("--decision", default="AUTO_SNAPSHOT")
    ap.add_argument("--reason", default="Daily governance snapshot append.")
    ap.add_argument("--ledger-jsonl", default="reports/mkm_decision_ledger.jsonl")
    ap.add_argument("--latest-json", default="docs/final/artifacts/mkm_decision_ledger_latest.json")
    args = ap.parse_args()

    root = resolve(args.workspace_root)
    p_status = root / "docs/final/artifacts/mkm_ai_status_pointer_latest.json"
    p_trackc = root / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
    p_atrack = root / "docs/final/artifacts/a_track_go_nogo_status_latest.json"
    p_prom = root / "docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json"
    p_ledger = resolve(args.ledger_jsonl)
    p_latest = resolve(args.latest_json)

    status = load_json(p_status) if p_status.is_file() else {}
    trackc = load_json(p_trackc) if p_trackc.is_file() else {}
    atrack = load_json(p_atrack) if p_atrack.is_file() else {}
    prom = load_json(p_prom) if p_prom.is_file() else {}

    row = {
        "schema": "mkm_decision_ledger_v1",
        "timestamp_utc": utc_now(),
        "decision": args.decision,
        "actor": args.actor,
        "reason": args.reason,
        "status_context": {
            "system_status": status.get("status"),
            "promotion_decision": status.get("decision"),
            "trackc_decision_state": (trackc.get("trackc") or {}).get("api_decision_state"),
            "a_track_go_no_go": (atrack.get("result") or {}).get("overall_go_no_go"),
            "a_track_stage": (atrack.get("result") or {}).get("recommended_stage"),
            "promotion_ready": prom.get("promotion_ready"),
        },
        "evidence_paths": [
            "docs/final/artifacts/mkm_ai_status_pointer_latest.json",
            "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json",
            "docs/final/artifacts/a_track_go_nogo_status_latest.json",
            "docs/final/artifacts/mkm_ai_v2_promotion_decision_latest.json",
        ],
    }

    p_ledger.parent.mkdir(parents=True, exist_ok=True)
    with p_ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    latest = {
        "schema": "mkm_decision_ledger_latest_v1",
        "generated_at_utc": row["timestamp_utc"],
        "last_row": row,
        "ledger_path": str(p_ledger),
    }
    p_latest.parent.mkdir(parents=True, exist_ok=True)
    p_latest.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"ledger appended: {p_ledger}")
    print(f"ledger latest written: {p_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
