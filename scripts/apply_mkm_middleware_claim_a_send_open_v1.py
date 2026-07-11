#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply commander SEND OPEN for Claim-A L0 onepager scope only.

Does NOT open Track A, live trading, or grant/customer blast.
Requires exchange_ready_computed + independent_blind + send_ready_fact_lock.

  py scripts/apply_mkm_middleware_claim_a_send_open_v1.py --acknowledge
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_middleware_llm_harness_lib_v1 import utc_now  # noqa: E402

CHECKLIST = ROOT / "docs/final/artifacts/mkm_middleware_anti_self_grade_checklist_v1_latest.json"
ONEPAGER = ROOT / "docs/final/artifacts/mkm_middleware_l0_send_ready_onepager_v1_latest.md"
OUT = ROOT / "docs/final/artifacts/mkm_middleware_claim_a_send_open_v1_latest.json"
CLAUDE = ROOT / "docs/final/artifacts/mkm_middleware_claim_a_claude_rereview_pack_v1_latest.md"
OUT_MIRROR = ROOT / "reports/mkm_middleware_claim_a_send_open_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--acknowledge",
        action="store_true",
        help="commander explicit SEND OPEN for L0 onepager + Claude research pack",
    )
    args = ap.parse_args()
    if not args.acknowledge:
        print("ERR: refuse without --acknowledge", file=sys.stderr)
        return 2

    cl = json.loads(CHECKLIST.read_text(encoding="utf-8-sig"))
    if not (
        cl.get("exchange_ready_computed")
        and cl.get("independent_blind")
        and cl.get("send_ready_fact_lock")
    ):
        print("ERR: checklist not exchange_ready", file=sys.stderr)
        return 1

    # Claude residual: headline checklist must be exit-gated, not manual-only doc
    from scripts.check_mkm_middleware_headline_reuse_guard_v1 import (  # noqa: WPS433
        write_checklist as _headline_checklist,
    )

    hl = _headline_checklist()
    if not hl.get("ok"):
        print(
            "ERR: headline_reuse_guard FAIL — fix orphan Send-pointers before SEND OPEN",
            file=sys.stderr,
        )
        print(f"checklist={hl.get('checks')}", file=sys.stderr)
        return 2
    print(f"headline_reuse_ok={hl.get('ok')} egress_onepager={hl.get('egress_hero_aligned_on_onepager')}")

    now = utc_now()
    doc = {
        "schema": "mkm_middleware_claim_a_send_open_v1",
        "version": "1.0.0",
        "generated_at_utc": now,
        "commander_acknowledge": True,
        "send_gate": "OPEN",
        "scope": [
            "L0_middleware_onepager",
            "claim_a_claude_research_pack",
        ],
        "not_opened": [
            "track_a",
            "live_trading",
            "grant_customer_blast",
            "logos_corpus_as_middleware_moat",
        ],
        "claude_exchange_a_claim_allowed": True,
        "research_only_metrics": True,
        "live_trading": "OFF",
        "note_ko": (
            "스코프 한정 SEND OPEN. Track A·실매매·고객 일괄 발송은 여전히 닫힘. "
            "수치 인용은 프로그램명+아티팩트 경로 필수."
        ),
        "onepager": str(ONEPAGER.relative_to(ROOT)).replace("\\", "/"),
        "checklist": str(CHECKLIST.relative_to(ROOT)).replace("\\", "/"),
        "headline_reuse_guard": {
            "ok": True,
            "script": "scripts/check_mkm_middleware_headline_reuse_guard_v1.py",
            "checklist": "docs/final/artifacts/mkm_middleware_headline_reuse_checklist_v1_latest.json",
            "enforced_on": "apply_mkm_middleware_claim_a_send_open_v1.py",
        },
    }
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8")
    OUT_MIRROR.write_text(text, encoding="utf-8")

    # Update checklist twin
    cl["send_gate"] = "OPEN"
    cl["claude_exchange_a_claim_allowed"] = True
    cl["commander_send_open_at_utc"] = now
    cl["commander_send_open_path"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
    cl["note_ko"] = (
        "지휘관 SEND OPEN(L0 onepager+Claude research pack). "
        "Track A·live trading 미개방. claim_A 허용은 스코프 한정."
    )
    cl["generated_at_utc"] = now
    CHECKLIST.write_text(json.dumps(cl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (
        ROOT / "reports/mkm_middleware_anti_self_grade_checklist_v1_latest.json"
    ).write_text(json.dumps(cl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Patch onepager header status
    md = ONEPAGER.read_text(encoding="utf-8")
    md2 = md.replace(
        "**Status:** `send_ready_draft` · **`SEND_GATE: HOLD`** until commander OPEN",
        "**Status:** `send_open_scoped` · **`SEND_GATE: OPEN`** (L0 onepager + Claude research pack only; Track A/live OFF)",
    )
    md2 = md2.replace(
        "- Not Exchange / Claude grade-A certification (research checklist incomplete for that bar).",
        "- Exchange / Claude research-pack use: **allowed under scoped SEND OPEN** "
        "(still not Track A / live trading / market-unique claims).",
    )
    md2 = md2.replace(
        "| Commercial SEND | **HOLD** (commander) |\n"
        "| Exchange / Claude A claim | **false** until independent human Blind + this draft Fact-Lock + commander OPEN |",
        "| Commercial SEND (L0 onepager scope) | **OPEN** (commander 2026-07-11) |\n"
        "| Exchange / Claude A claim (scoped) | **true** — still cite program+artifact; no Track A |\n"
        "| Track A / live trading | **OFF** |",
    )
    ONEPAGER.write_text(md2, encoding="utf-8")

    claude = f"""## Claude 제출 팩 — SEND OPEN (scoped · exit 0)

### Guard
- **`SEND_GATE: OPEN`** — scope: L0 onepager + this research pack only
- Track A · live trading · grant blast · scripture-as-middleware-moat: **OFF**
- `claude_exchange_a_claim_allowed=true` (scoped)
- Cite metrics only with program name + artifact path

### Checklist
- [x] 외부 ≥2 · n≥30 · fair plain
- [x] Blind≥20 · independent_blind (`commander_human`)
- [x] SEND-ready Fact-Lock
- [x] Commander SEND OPEN

### Paste targets
- One-pager: `docs/final/artifacts/mkm_middleware_l0_send_ready_onepager_v1_latest.md`
- Open record: `docs/final/artifacts/mkm_middleware_claim_a_send_open_v1_latest.json`
- Stamp: `docs/final/artifacts/mkm_middleware_anti_self_grade_checklist_v1_latest.json`

### Headline (allowed · rev 1.7 egress — not usefulness)
> Keep the corpus local. What leaves your boundary: pointers, locked citations, and a hard HOLD — never the corpus itself.

Claim frame: egress / security — not a usefulness claim. Legacy "Send pointers" = research ledger only with Counter-signal (plain_full prefer tension).
Gate: `py scripts/check_mkm_middleware_headline_reuse_guard_v1.py` (exit 0/2).

### Measured (research)
- chars save vs plain ≈ 0.73 (fair external AB n=30)
- Azure fair: id gate ≈ 0.80 / plain ≈ 0.30
- HOLD remasure: plain hold 0.58→1.00 @ max_tokens 1024
- Gemini HOLD-first: hold 0.33→1.00 / gate→0.92 (n=12)

generated_at_utc: `{now}`
"""
    CLAUDE.write_text(claude, encoding="utf-8")

    print(f"WROTE: {OUT}")
    print(f"UPDATED: {ONEPAGER}")
    print(f"UPDATED: {CLAUDE}")
    print("send_gate=OPEN scoped claim_A=true track_a=OFF live=OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
