#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

ART = ROOT / "docs" / "final" / "artifacts"
CANONICAL_SELECTIVE_OUT = ART / "trackb_action_layer_selective_state_sim_latest.json"
CANONICAL_SELECTIVE_TRIGGER_OUT = ART / "trackb_action_layer_selective_state_sim_triggercase_latest.json"
LEGACY_SELECTIVE_OUT = ART / "trackb_selective_state_sim_latest.json"
LEGACY_SELECTIVE_TRIGGER_OUT = ART / "trackb_selective_state_sim_triggercase_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tokenize(s: str) -> list[str]:
    import re

    return re.findall(r"[A-Za-z0-9가-힣]+", s.lower())


@dataclass
class SimConfig:
    forget_factor: float = 0.90
    m_trigger_threshold: float = 0.85
    confidence_threshold: float = 0.75
    cooldown_sec: int = 5


class SelectiveStateEngine:
    """Mamba-like selective state update simulator (not real Mamba)."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.state = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
        self.last_trigger_ts: float | None = None

    def _score_sentence(self, text: str) -> dict[str, float]:
        tks = _tokenize(text)
        n = max(1, len(tks))
        # Lightweight heuristic projection to 4D
        action_tokens = {"alert", "risk", "critical", "경보", "위험", "즉시", "긴급"}
        search_tokens = {"search", "evidence", "근거", "조회", "query"}
        material_tokens = {"apply", "execute", "trigger", "실행", "격발", "적용"}
        stable_tokens = {"stable", "normal", "안정", "유지"}

        hits_action = sum(1 for x in tks if x in action_tokens)
        hits_search = sum(1 for x in tks if x in search_tokens)
        hits_material = sum(1 for x in tks if x in material_tokens)
        hits_stable = sum(1 for x in tks if x in stable_tokens)

        return {
            "S": min(1.0, (hits_stable / n) + 0.10),
            "L": min(1.0, (hits_search / n) + 0.15),
            "K": min(1.0, (hits_action / n) + 0.20),
            "M": min(1.0, (hits_material / n) + (hits_action / n) + 0.25),
        }

    def step(self, text: str, confidence: float, policy_ok: bool, now_ts: float) -> dict[str, Any]:
        obs = self._score_sentence(text)
        # selective forget + update
        for k in self.state:
            self.state[k] = min(1.0, (self.state[k] * self.cfg.forget_factor) + ((1 - self.cfg.forget_factor) * obs[k]))

        trigger_reason = None
        decision = "state_update_only"
        if not policy_ok:
            decision = "json_fallback"
            trigger_reason = "policy_blocked"
        elif confidence < self.cfg.confidence_threshold:
            decision = "json_fallback"
            trigger_reason = "confidence_below_threshold"
        elif self.state["M"] >= self.cfg.m_trigger_threshold:
            if self.last_trigger_ts is not None and (now_ts - self.last_trigger_ts) < self.cfg.cooldown_sec:
                decision = "json_fallback"
                trigger_reason = "cooldown_active"
            else:
                decision = "action_triggered"
                trigger_reason = "m_threshold_reached"
                self.last_trigger_ts = now_ts

        return {
            "observation": obs,
            "state": {k: round(v, 8) for k, v in self.state.items()},
            "decision": decision,
            "reason": trigger_reason,
            "policy_ok": policy_ok,
            "confidence": confidence,
        }


def _default_stream() -> list[dict[str, Any]]:
    return [
        {"id": "s1", "text": "환자 상태 안정 유지, 근거 조회 필요", "confidence": 0.83, "policy_ok": True},
        {"id": "s2", "text": "critical risk detected, execute alert trigger now", "confidence": 0.88, "policy_ok": True},
        {"id": "s3", "text": "위험 경보 즉시 실행 trigger 적용", "confidence": 0.90, "policy_ok": True},
        {"id": "s4", "text": "query evidence only", "confidence": 0.79, "policy_ok": False},
        {"id": "s5", "text": "execute alert risk", "confidence": 0.81, "policy_ok": True},
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B selective state simulator for action-trigger logic")
    ap.add_argument("--stream", default="", help="Optional JSONL stream path")
    ap.add_argument("--forget-factor", type=float, default=0.90)
    ap.add_argument("--m-threshold", type=float, default=0.85)
    ap.add_argument("--confidence-threshold", type=float, default=0.75)
    ap.add_argument("--cooldown-sec", type=int, default=5)
    ap.add_argument("--out", default=str(CANONICAL_SELECTIVE_OUT))
    args = ap.parse_args()

    if args.stream:
        p = Path(args.stream) if Path(args.stream).is_absolute() else (ROOT / args.stream)
        stream = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    else:
        stream = _default_stream()

    cfg = SimConfig(
        forget_factor=args.forget_factor,
        m_trigger_threshold=args.m_threshold,
        confidence_threshold=args.confidence_threshold,
        cooldown_sec=args.cooldown_sec,
    )
    engine = SelectiveStateEngine(cfg)

    now = time.time()
    logs = []
    for i, row in enumerate(stream):
        ts = now + i
        out = engine.step(
            text=str(row.get("text", "")),
            confidence=float(row.get("confidence", 0.0)),
            policy_ok=bool(row.get("policy_ok", False)),
            now_ts=ts,
        )
        logs.append({"id": row.get("id", f"row_{i}"), "input": row, "output": out})

    action_count = sum(1 for x in logs if x["output"]["decision"] == "action_triggered")
    fallback_count = sum(1 for x in logs if x["output"]["decision"] == "json_fallback")
    event_count = len(logs)

    out_doc = {
        "schema": "trackb_action_layer_selective_state_sim_v1",
        "generated_at_utc": _utc_now(),
        "config": {
            "forget_factor": cfg.forget_factor,
            "m_trigger_threshold": cfg.m_trigger_threshold,
            "confidence_threshold": cfg.confidence_threshold,
            "cooldown_sec": cfg.cooldown_sec,
        },
        "summary": {
            "event_count": event_count,
            "action_triggered_count": action_count,
            "fallback_count": fallback_count,
            "action_trigger_rate": round(action_count / max(1, event_count), 8),
            "fallback_rate": round(fallback_count / max(1, event_count), 8),
        },
        "logs": logs,
        "fact_safe_note": "This is a selective-state logic simulator, not a production Mamba model benchmark.",
        "out_of_scope": "No production promotion, no trading trigger, no paid external side effect.",
    }

    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if out_path.resolve() in (
        CANONICAL_SELECTIVE_OUT.resolve(),
        CANONICAL_SELECTIVE_TRIGGER_OUT.resolve(),
    ):
        from trackb_artifact_alias_util import write_alias

        if out_path.resolve() == CANONICAL_SELECTIVE_OUT.resolve():
            write_alias(
                legacy_path=LEGACY_SELECTIVE_OUT,
                canonical_relative="docs/final/artifacts/trackb_action_layer_selective_state_sim_latest.json",
            )
        else:
            write_alias(
                legacy_path=LEGACY_SELECTIVE_TRIGGER_OUT,
                canonical_relative="docs/final/artifacts/trackb_action_layer_selective_state_sim_triggercase_latest.json",
            )
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
