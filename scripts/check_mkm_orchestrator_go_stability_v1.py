#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CURRENT = ART / "mkm_global_orchestrator_latest.json"
DEFAULT_PREVIOUS = ART / "mkm_global_orchestrator_previous_snapshot.json"
DEFAULT_OUT = ART / "mkm_global_orchestrator_go_stability_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _result(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("result") if isinstance(doc.get("result"), dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Check GO stability and detect down transitions.")
    ap.add_argument("--current-json", type=Path, default=DEFAULT_CURRENT)
    ap.add_argument("--previous-json", type=Path, default=DEFAULT_PREVIOUS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--refresh-previous", action="store_true", help="Persist current as previous snapshot.")
    args = ap.parse_args()

    current_path = args.current_json if args.current_json.is_absolute() else ROOT / args.current_json
    previous_path = args.previous_json if args.previous_json.is_absolute() else ROOT / args.previous_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    current_doc = _read_json(current_path)
    current_res = _result(current_doc)
    current_decision = str(current_res.get("decision") or "HOLD").upper()

    previous_exists = previous_path.exists()
    previous_decision = "UNKNOWN"
    transition = "initial"
    down_transition = False
    if previous_exists:
        previous_doc = _read_json(previous_path)
        previous_res = _result(previous_doc)
        previous_decision = str(previous_res.get("decision") or "UNKNOWN").upper()
        transition = f"{previous_decision}->{current_decision}"
        down_transition = previous_decision == "GO" and current_decision in {"WATCH", "HOLD"}

    go_stable = current_decision == "GO" and not down_transition
    report = {
        "schema": "mkm_orchestrator_go_stability_v1",
        "generated_at_utc": _now(),
        "current_decision": current_decision,
        "previous_decision": previous_decision,
        "transition": transition,
        "down_transition_detected": down_transition,
        "go_stable": go_stable,
        "evidence": {
            "current_json": str(current_path),
            "previous_json": str(previous_path),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.refresh_previous:
        previous_path.parent.mkdir(parents=True, exist_ok=True)
        previous_path.write_text(json.dumps(current_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(out_path), "go_stable": go_stable, "transition": transition}, ensure_ascii=False))
    return 0 if go_stable else 1


if __name__ == "__main__":
    raise SystemExit(main())
