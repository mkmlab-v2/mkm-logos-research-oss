#!/usr/bin/env python3
"""Oracle Logos B2B WTP discovery readiness — aggregate + commander next steps.

Automates summary build only; 3 calls remain human.
Exit 0 always when template/playbook present.

Reproduce:
  py scripts/run_oracle_logos_wtp_discovery_readiness_v1.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SUMMARY = ROOT / "reports/logos_studio_b2b_wtp_discovery_summary_v1_latest.json"
PLAYBOOK = ROOT / "reports/logos_studio_b2b_wtp_discovery_call_playbook_v1.md"
TEMPLATE = ROOT / "reports/logos_studio_b2b_wtp_discovery_memo_template_v1.md"
OUT = ROOT / "reports/oracle_logos_wtp_discovery_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _call_memo_status(n: int) -> dict[str, Any]:
    path = ROOT / f"reports/logos_studio_b2b_wtp_discovery_call_{n}_v1.md"
    if not path.is_file():
        return {"call": n, "exists": False, "status": "missing"}
    text = path.read_text(encoding="utf-8-sig")
    pending = "Status:** `pending`" in text or "**Status:** `pending`" in text
    return {
        "call": n,
        "exists": True,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "status": "pending" if pending else "maybe_completed",
    }


def main() -> int:
    build = ROOT / "scripts/build_logos_studio_b2b_wtp_discovery_summary_v1.py"
    if build.is_file():
        subprocess.run([PY, str(build)], cwd=ROOT, check=False)

    summary: dict[str, Any] = {}
    if SUMMARY.is_file():
        summary = json.loads(SUMMARY.read_text(encoding="utf-8-sig"))

    calls = [_call_memo_status(i) for i in (1, 2, 3)]
    completed = int(summary.get("calls_completed") or 0)
    awaiting = 3 - completed

    next_actions: list[str] = []
    if awaiting > 0:
        for c in calls:
            if c.get("status") != "maybe_completed":
                n = c["call"]
                anchor = {1: "390만", 2: "490만", 3: "590만"}[n]
                next_actions.append(
                    f"콜 {n}: playbook §2 따라 파일럿 ₩{anchor} 앵커 — "
                    f"reports/logos_studio_b2b_wtp_discovery_call_{n}_v1.md 작성 후 "
                    f"py scripts/build_logos_studio_b2b_wtp_discovery_summary_v1.py"
                )
    else:
        next_actions.append("3콜 완료 — promotion_decision 검토 (pricing §7, SEND_GATE HOLD 유지)")

    doc = {
        "schema": "oracle_logos_wtp_discovery_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "lane": "oracle",
        "status": "awaiting_commander_calls" if awaiting else "calls_complete_review",
        "calls_completed": completed,
        "calls_required": 3,
        "calls_awaiting": awaiting,
        "demo_url": (
            "https://logos.jema-ai.com/logos-research/studio"
            "?q=job_job_suffering_reason&autorun=1&demo=1"
        ),
        "playbook_md": str(PLAYBOOK.relative_to(ROOT)).replace("\\", "/"),
        "template_md": str(TEMPLATE.relative_to(ROOT)).replace("\\", "/"),
        "summary_json": str(SUMMARY.relative_to(ROOT)).replace("\\", "/"),
        "promotion_decision": summary.get("promotion_decision", "research_only_until_3_calls_complete"),
        "call_memos": calls,
        "commander_next_actions": next_actions,
        "automated_note_ko": "WTP 콜 본문은 인간만 — 본 스크립트는 집계·체크리스트만 갱신.",
        "reproduce": "py scripts/run_oracle_logos_wtp_discovery_readiness_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = ROOT / "docs/final/artifacts/oracle_logos_wtp_discovery_readiness_v1_latest.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "calls_awaiting": awaiting, "artifact": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
