#!/usr/bin/env python3
"""Append latest staged fusion outcome to shadow history jsonl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status-json", type=Path, default=ART / "three_lens_staged_inclusion_status_latest.json")
    ap.add_argument("--gate-json", type=Path, default=ART / "three_lens_feature_gate_v2_latest.json")
    ap.add_argument("--history-jsonl", type=Path, default=ART / "three_lens_shadow_history_v1.jsonl")
    args = ap.parse_args()

    status = _read_json(args.status_json if args.status_json.is_absolute() else ROOT / args.status_json)
    gate = _read_json(args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json)
    out = args.history_jsonl if args.history_jsonl.is_absolute() else ROOT / args.history_jsonl

    row = {
        "ts_utc": _now(),
        "status_hint": status.get("decision_hint"),
        "enabled_evidence_all_present": ((status.get("summary") or {}).get("enabled_evidence_all_present") is True),
        "shadow_missing_count": int((status.get("summary") or {}).get("shadow_missing_count") or 0),
        "action": (gate.get("decision") or {}).get("action", "WATCH"),
        "reason": (gate.get("decision") or {}).get("reason"),
        "risk_score_0_1": float((gate.get("metrics") or {}).get("risk_score_0_1") or 0.0),
        "opportunity_score_0_1": float((gate.get("metrics") or {}).get("opportunity_score_0_1") or 0.0),
        "source_action": (gate.get("metrics") or {}).get("source_action"),
        "logos_non_gating_ok": bool((gate.get("metrics") or {}).get("logos_non_gating_ok") is True),
        "conditional_go_enabled": bool((gate.get("metrics") or {}).get("conditional_go_enabled") is True),
        "conditional_go_armed": bool((gate.get("metrics") or {}).get("conditional_go_armed") is True),
        "watch_bias_ratio": float((gate.get("metrics") or {}).get("watch_bias_ratio") or 0.0),
        "external_intel_guard_failed": bool((gate.get("metrics") or {}).get("external_intel_guard_failed") is True),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "history_jsonl": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
