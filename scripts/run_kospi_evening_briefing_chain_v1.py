#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evening briefing primary chain — parallel advisory GraphRAG + premium synthesis [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_prophecy_lane_routing_v1 import BRIEFING_LANE_ID, build_routing_manifest  # noqa: E402

PY = sys.executable
KST = ZoneInfo("Asia/Seoul")
OUT = ROOT / "reports/kospi_evening_briefing_chain_v1_latest.json"
ART = ROOT / "docs/final/artifacts/kospi_evening_briefing_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _last_krx() -> str:
    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    return last_krx_trading_day_on_or_before(datetime.now(KST).date()) or _today_kst()


def run_step(name: str, cmd: list[str], *, optional: bool = False) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    row = {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": (proc.stdout or proc.stderr or "")[-500:],
        "optional": optional,
    }
    if proc.returncode != 0 and optional:
        row["skipped_as_optional"] = True
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-date", default=None, help="KST session anchor (default last KRX)")
    ap.add_argument("--domain", default="finance")
    ap.add_argument("--skip-science-merge", action="store_true")
    ap.add_argument("--skip-premium", action="store_true")
    ap.add_argument("--skip-routing-manifest", action="store_true")
    ns = ap.parse_args()

    session = (ns.session_date or _last_krx())[:10]
    steps: list[dict[str, Any]] = []

    if not ns.skip_science_merge:
        from datetime import timedelta

        sess_d = datetime.strptime(session, "%Y-%m-%d").date()
        d_from = (sess_d - timedelta(days=14)).isoformat()
        steps.append(
            run_step(
                "merge_science_core_kospi",
                [
                    PY,
                    "scripts/merge_btrack_science_core_per_date_kospi_v1.py",
                    "--date-from",
                    d_from,
                    "--date-to",
                    session,
                ],
                optional=True,
            )
        )

    steps.append(
        run_step(
            "parallel_advisory_chain",
            [
                PY,
                "scripts/run_mkm_parallel_advisory_chain_v1.py",
                "--domain",
                ns.domain,
                "--session-date",
                session,
            ],
        )
    )

    if not ns.skip_premium:
        steps.append(
            run_step(
                "premium_multilens_best_effort",
                [
                    PY,
                    "scripts/build_premium_btrack_multilens_report_v1.py",
                    "--mode",
                    "best-effort",
                    "--no-validate",
                ],
                optional=True,
            )
        )

    blocking = [s for s in steps if s.get("exit_code", 0) != 0 and not s.get("optional")]
    ok = not blocking

    doc: dict[str, Any] = {
        "schema": "kospi_evening_briefing_chain_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "prophecy_lane": BRIEFING_LANE_ID,
        "prophecy_lane_role": "briefing_primary",
        "session_date_kst": session,
        "domain_id": ns.domain,
        "ok": ok,
        "steps": steps,
        "blocking_failures": [s["name"] for s in blocking],
        "outputs": {
            "parallel_advisory_brief": "reports/mkm_parallel_advisory_brief_v1_latest.json",
            "four_lens_fusion_md": "reports/kospi_four_lens_graphrag_fusion_v1_latest.md",
            "premium_report": "reports/premium_btrack_multilens_report_v1_latest.json",
        },
        "do_not_confuse_ko": (
            "본 체인=통찰 브리핑 본선. kospi_direction HR은 scoring_shadow(weighted_blend) — 별도."
        ),
        "reproduce": f"py scripts/run_kospi_evening_briefing_chain_v1.py --session-date {session}",
    }

    for p in (OUT, ART):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not ns.skip_routing_manifest:
        routing = build_routing_manifest(session_date=session, evening_chain_doc=doc)
        for rp in (
            ROOT / "reports/kospi_prophecy_lane_routing_v1_latest.json",
            ROOT / "docs/final/artifacts/kospi_prophecy_lane_routing_v1_latest.json",
        ):
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(json.dumps(routing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": ok, "session_date": session, "out": str(OUT), "steps": len(steps)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
