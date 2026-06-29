#!/usr/bin/env python3
"""Merge engineering probe + Playwright design checks → design readiness SSOT.

consumer_ready is True only when engineering_ok AND design_ok AND commander_visual_ok is not False.
Agents must NOT claim holistic 「잘 됨」 when consumer_ready is false.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/magic_orb_design_readiness_v1_latest.json"
ENGINEERING_PROBE = ROOT / "reports/magic_orb_live_probe_latest.json"
PLAYWRIGHT = ROOT / "reports/magic_orb_design_readiness_playwright_v1_latest.json"
SCREENSHOT = ROOT / "reports/magic_orb_design_screenshot_latest.png"
COMMANDER_VISUAL = ROOT / "reports/magic_orb_commander_visual_review_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _commander_visual_from_ssot() -> bool | None:
    doc = _read_json(COMMANDER_VISUAL)
    if not doc:
        return None
    v = doc.get("commander_visual_ok")
    if v is True:
        return True
    if v is False:
        return False
    return None


def build(
    *,
    engineering_doc: dict[str, Any] | None,
    playwright_doc: dict[str, Any] | None,
    commander_visual_ok: bool | None,
) -> dict[str, Any]:
    engineering_ok = bool(engineering_doc and engineering_doc.get("all_ok"))
    design_reviewed = bool(playwright_doc and not playwright_doc.get("skipped"))
    design_ok = bool(playwright_doc and playwright_doc.get("design_ok"))
    screenshot_ok = SCREENSHOT.is_file()

    if commander_visual_ok is False:
        consumer_ready = False
    elif commander_visual_ok is True:
        consumer_ready = engineering_ok and design_ok
    else:
        consumer_ready = False

    failed = [
        c.get("id")
        for c in (playwright_doc or {}).get("checks") or []
        if c.get("consumer_blocker", True) and not c.get("ok")
    ]

    if not engineering_ok:
        verdict = "engineering 미통과 — holistic 「잘 됨」 금지"
    elif not design_reviewed:
        verdict = "design 미검토 — holistic 「잘 됨」 금지"
    elif not design_ok:
        verdict = "engineering OK · design FAIL — POC 쇼룸 (허접/미정리 가능)"
    elif commander_visual_ok is None:
        verdict = "engineering+design 자동 OK · commander 시각 확인 대기"
    elif commander_visual_ok is False:
        verdict = "commander design 거부 — consumer_ready false"
    else:
        verdict = "consumer_ready true — holistic 「잘 됨」 허용"

    return {
        "schema": "magic_orb_design_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "engineering_ok": engineering_ok,
        "design_reviewed": design_reviewed,
        "design_ok": design_ok,
        "screenshot_ok": screenshot_ok,
        "commander_visual_ok": commander_visual_ok,
        "consumer_ready": consumer_ready,
        "verdict_ko": verdict,
        "design_fail_ids": failed,
        "artifacts": {
            "engineering_probe": str(ENGINEERING_PROBE.relative_to(ROOT)).replace("\\", "/"),
            "playwright": str(PLAYWRIGHT.relative_to(ROOT)).replace("\\", "/"),
            "screenshot": str(SCREENSHOT.relative_to(ROOT)).replace("\\", "/"),
        },
        "engineering_probe_profile": (engineering_doc or {}).get("profile"),
        "playwright_checks": (playwright_doc or {}).get("checks"),
        "messaging_contract": {
            "allowed_when_consumer_ready_false": [
                "engineering/probe 축 통과 (기능·배포)",
                "design FAIL · POC · commander 확인 필요",
            ],
            "disallowed_when_consumer_ready_false": [
                "관측 구 디자인/UX 「잘 됨」",
                "소비자 제품 완성",
                "probe all_ok = 제품 OK",
            ],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--engineering-probe", type=Path, default=ENGINEERING_PROBE)
    ap.add_argument("--playwright-json", type=Path, default=PLAYWRIGHT)
    ap.add_argument(
        "--commander-visual-ok",
        choices=("true", "false", "unset"),
        default="unset",
        help="Human visual pass (unset → read magic_orb_commander_visual_review_v1_latest.json if present)",
    )
    ap.add_argument("--strict-consumer", action="store_true", help="exit 1 if not consumer_ready")
    args = ap.parse_args()

    cvo: bool | None
    if args.commander_visual_ok == "true":
        cvo = True
    elif args.commander_visual_ok == "false":
        cvo = False
    else:
        cvo = _commander_visual_from_ssot()

    doc = build(
        engineering_doc=_read_json(args.engineering_probe),
        playwright_doc=_read_json(args.playwright_json),
        commander_visual_ok=cvo,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rel = args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(rel).replace("\\", "/"),
                "consumer_ready": doc["consumer_ready"],
                "engineering_ok": doc["engineering_ok"],
                "design_ok": doc["design_ok"],
                "verdict_ko": doc["verdict_ko"],
            },
            ensure_ascii=False,
        )
    )
    if args.strict_consumer and not doc["consumer_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
