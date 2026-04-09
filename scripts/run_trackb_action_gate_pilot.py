#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
CANONICAL_ACTION_GATE_OUT = ART / "trackb_action_layer_gate_pilot_latest.json"
LEGACY_ACTION_GATE_OUT = ART / "trackb_action_gate_pilot_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class GateConfig:
    m_threshold: float = 0.85
    confidence_threshold: float = 0.75
    cooldown_sec: int = 5
    require_policy_ok: bool = True


class ActionRouter:
    """Low-risk action router for Track B pilot."""

    def __init__(self, cfg: GateConfig) -> None:
        self.cfg = cfg
        self.last_fired_ts: dict[str, float] = {}

    def _cooldown_ok(self, action: str, now_ts: float) -> bool:
        prev = self.last_fired_ts.get(action)
        if prev is None:
            return True
        return (now_ts - prev) >= self.cfg.cooldown_sec

    def _gate_ok(self, event: dict[str, Any], action: str, now_ts: float) -> tuple[bool, str]:
        if self.cfg.require_policy_ok and not bool(event.get("policy_ok", False)):
            return False, "policy_blocked"
        if float(event.get("M", 0.0)) < self.cfg.m_threshold:
            return False, "m_below_threshold"
        if float(event.get("confidence", 0.0)) < self.cfg.confidence_threshold:
            return False, "confidence_below_threshold"
        if not self._cooldown_ok(action, now_ts):
            return False, "cooldown_active"
        return True, "gate_pass"

    def route(self, event: dict[str, Any], now_ts: float) -> dict[str, Any]:
        requested = str(event.get("requested_action", "notify"))
        action = requested if requested in {"notify", "query", "enqueue"} else "notify"
        ok, reason = self._gate_ok(event, action, now_ts)
        if ok:
            self.last_fired_ts[action] = now_ts
            return {"decision": "action_fire", "action": action, "reason": reason}
        # rollback path: safe JSON output only
        return {"decision": "json_fallback", "action": None, "reason": reason}


def _default_events() -> list[dict[str, Any]]:
    return [
        {"id": "e1", "M": 0.91, "confidence": 0.84, "policy_ok": True, "requested_action": "notify"},
        {"id": "e2", "M": 0.87, "confidence": 0.82, "policy_ok": True, "requested_action": "enqueue"},
        {"id": "e3", "M": 0.71, "confidence": 0.91, "policy_ok": True, "requested_action": "query"},
        {"id": "e4", "M": 0.92, "confidence": 0.77, "policy_ok": False, "requested_action": "notify"},
        {"id": "e5", "M": 0.93, "confidence": 0.88, "policy_ok": True, "requested_action": "notify"},
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B low-risk action-gate pilot")
    ap.add_argument("--events", default="", help="Optional JSONL events path")
    ap.add_argument("--out", default=str(CANONICAL_ACTION_GATE_OUT))
    ap.add_argument("--m-threshold", type=float, default=0.85)
    ap.add_argument("--confidence-threshold", type=float, default=0.75)
    ap.add_argument("--cooldown-sec", type=int, default=5)
    args = ap.parse_args()

    if args.events:
        p = Path(args.events) if Path(args.events).is_absolute() else (ROOT / args.events)
        events = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    else:
        events = _default_events()

    cfg = GateConfig(
        m_threshold=args.m_threshold,
        confidence_threshold=args.confidence_threshold,
        cooldown_sec=args.cooldown_sec,
        require_policy_ok=True,
    )
    router = ActionRouter(cfg)

    now_ts = time.time()
    logs = []
    for i, e in enumerate(events):
        ts = now_ts + i  # deterministic progression for cooldown simulation
        result = router.route(e, ts)
        logs.append({"event": e, "result": result})

    fired = [x for x in logs if x["result"]["decision"] == "action_fire"]
    fallback = [x for x in logs if x["result"]["decision"] == "json_fallback"]

    out = {
        "schema": "trackb_action_layer_gate_pilot_v1",
        "generated_at_utc": _utc_now(),
        "config": {
            "m_threshold": cfg.m_threshold,
            "confidence_threshold": cfg.confidence_threshold,
            "cooldown_sec": cfg.cooldown_sec,
            "require_policy_ok": cfg.require_policy_ok,
        },
        "summary": {
            "event_count": len(logs),
            "action_fire_count": len(fired),
            "fallback_count": len(fallback),
        },
        "logs": logs,
        "safety": {
            "low_risk_actions_only": True,
            "no_production_side_effect": True,
            "rollback_mode": "json_fallback",
        },
        "out_of_scope": "No production promotion, no trading trigger, no paid external side effect.",
    }

    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if out_path.resolve() == CANONICAL_ACTION_GATE_OUT.resolve():
        from trackb_artifact_alias_util import write_alias

        write_alias(
            legacy_path=LEGACY_ACTION_GATE_OUT,
            canonical_relative="docs/final/artifacts/trackb_action_layer_gate_pilot_latest.json",
        )
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
