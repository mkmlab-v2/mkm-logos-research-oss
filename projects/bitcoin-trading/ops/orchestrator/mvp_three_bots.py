#!/usr/bin/env python3
"""MVP orchestrator for Athena + Watchdog + Brain Sync."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_DIR = PROJECT_ROOT / "memory"
KPI_JSON = MEMORY_DIR / "kpi" / "latest_kpi.json"
BRAIN_MD = MEMORY_DIR / "brain_sync" / "latest.md"
OUT_DIR = MEMORY_DIR / "orchestrator"


@dataclass
class WatchdogAssessment:
    risk_level: str
    action_hint: str
    issues: list[str]


@dataclass
class BrainSyncAssessment:
    sync_fresh: bool
    note_path: str
    summary: str


class WatchdogBot:
    def evaluate(self, kpi: dict) -> WatchdogAssessment:
        issues: list[str] = []
        scheduler_ready = bool(kpi.get("scheduler_ready"))
        kill_switch_on = bool(kpi.get("kill_switch_on"))
        hb = kpi.get("heartbeat_age_min")
        running = kpi.get("status_running")

        if not scheduler_ready:
            issues.append("Scheduler not ready")
        if kill_switch_on:
            issues.append("Kill switch is ON")
        if hb is None or hb > 15:
            issues.append("Heartbeat stale or missing")
        if running is False:
            issues.append("Daemon not running")

        if kill_switch_on:
            return WatchdogAssessment("high", "PAUSE", issues)
        if issues:
            return WatchdogAssessment("medium", "RESTART", issues)
        return WatchdogAssessment("low", "KEEP", issues)


class BrainSyncBot:
    def evaluate(self, note_path: Path) -> BrainSyncAssessment:
        if not note_path.exists():
            return BrainSyncAssessment(False, str(note_path), "Brain sync note missing")

        content = note_path.read_text(encoding="utf-8", errors="ignore")
        sync_fresh = "Runtime Snapshot" in content and "Watchdog Event Summary" in content
        summary = "Brain sync note is available" if sync_fresh else "Brain sync note format incomplete"
        return BrainSyncAssessment(sync_fresh, str(note_path), summary)


class AthenaBot:
    def decide(self, wd: WatchdogAssessment, bs: BrainSyncAssessment) -> dict:
        if wd.action_hint == "PAUSE":
            return {
                "decision": "PAUSE_WITH_KILL_SWITCH",
                "reason": "; ".join(wd.issues) or "Kill switch policy",
                "requires_human_approval": False,
            }
        if wd.action_hint == "RESTART":
            return {
                "decision": "REQUEST_RESTART",
                "reason": "; ".join(wd.issues) or "Runtime instability",
                "requires_human_approval": False,
            }
        if not bs.sync_fresh:
            return {
                "decision": "KEEP_RUNNING",
                "reason": "Runtime healthy but brain sync stale; regenerate note",
                "requires_human_approval": False,
            }
        return {
            "decision": "KEEP_RUNNING",
            "reason": "Runtime and brain sync healthy",
            "requires_human_approval": False,
        }


def _safe_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    kpi = _safe_json(KPI_JSON)
    wd = WatchdogBot().evaluate(kpi)
    bs = BrainSyncBot().evaluate(BRAIN_MD)
    decision = AthenaBot().decide(wd, bs)

    payload = {
        "ts_utc": now.isoformat(),
        "watchdog": {
            "risk_level": wd.risk_level,
            "action_hint": wd.action_hint,
            "issues": wd.issues,
        },
        "brain_sync": {
            "sync_fresh": bs.sync_fresh,
            "note_path": bs.note_path,
            "summary": bs.summary,
        },
        "athena": decision,
    }

    latest = OUT_DIR / "mvp_three_bots_latest.json"
    journal = OUT_DIR / f"mvp_three_bots_{now.strftime('%Y%m%d')}.jsonl"

    latest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with journal.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
