#!/usr/bin/env python3
"""Build btc_frame_governance_stage_payload_v1 JSON for runtime gate use."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "docs" / "final" / "artifacts" / "btc_frame_governance_stage_payload_v1_template.json"
DEFAULT_RISK = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
DEFAULT_APPROVAL = ROOT / "reports" / "trading_human_execution_approval_latest.json"
DEFAULT_OUT = ROOT / "reports" / "btc_frame_governance_stage_payload_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"JSON object expected: {path}")
    return obj


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(p.resolve())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    ap.add_argument("--risk-json", type=Path, default=DEFAULT_RISK)
    ap.add_argument("--approval-json", type=Path, default=DEFAULT_APPROVAL)
    ap.add_argument("--track", choices=("A", "B"), default="A")
    ap.add_argument("--stage", choices=("trinity", "bridge", "gate"), default="gate")
    ap.add_argument("--execution-mode", choices=("observe", "dry_run", "live"), default="live")
    ap.add_argument("--action", choices=("hold", "reduce", "watch", "go"), default="go")
    ap.add_argument("--position-size-pct", type=float, default=10.0)
    ap.add_argument("--confidence-score", type=float, default=0.85)
    ap.add_argument("--min-conf-threshold", type=float, default=0.8)
    ap.add_argument("--regime-gate-passed", action="store_true", default=True)
    ap.add_argument("--prophecy-wired", action="store_true", default=False)
    ap.add_argument("--live-allowed", action="store_true", default=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    template_path = args.template if args.template.is_absolute() else (ROOT / args.template)
    risk_path = args.risk_json if args.risk_json.is_absolute() else (ROOT / args.risk_json)
    approval_path = args.approval_json if args.approval_json.is_absolute() else (ROOT / args.approval_json)
    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)

    doc = _load_json(template_path.resolve())
    if "inputs" not in doc or "gate_input" not in (doc.get("inputs") or {}):
        raise ValueError("Template must include inputs.gate_input for gate runtime payload.")

    doc["schema"] = "btc_frame_governance_stage_payload_v1"
    doc["track"] = args.track
    doc["stage"] = args.stage
    doc.setdefault("inputs", {}).setdefault("gate_input", {})["risk_profile_ref"] = _rel(risk_path)
    doc["inputs"]["gate_input"]["execution_mode"] = args.execution_mode
    doc.setdefault("outputs", {})["action"] = args.action
    doc["outputs"]["position_size_pct"] = float(args.position_size_pct)
    doc["outputs"]["confidence_score"] = float(args.confidence_score)
    doc.setdefault("risk_gate", {})["regime_gate_passed"] = bool(args.regime_gate_passed)
    doc["risk_gate"]["prophecy_wired"] = bool(args.prophecy_wired)
    doc["risk_gate"]["human_approval_required"] = True
    doc["risk_gate"]["human_approval_ref"] = _rel(approval_path)
    doc["risk_gate"]["live_allowed"] = bool(args.live_allowed)
    doc["risk_gate"]["min_conf_threshold"] = float(args.min_conf_threshold)
    doc.setdefault("audit", []).append(
        {
            "ts_utc": _utc_now(),
            "actor": "build_btc_frame_governance_payload_v1",
            "decision": args.action if args.action in {"hold", "reduce", "watch", "go"} else "deny",
            "message": "Payload generated for conditional gate runtime.",
        }
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

