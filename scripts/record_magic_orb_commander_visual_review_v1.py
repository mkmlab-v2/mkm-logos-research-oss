#!/usr/bin/env python3
"""Record commander visual review for Magic Orb design readiness SSOT.

Tier: open_beta_poc — allows consumer_ready when engineering+design auto OK,
but does NOT claim finished product or Track A readiness.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/magic_orb_commander_visual_review_v1_latest.json"
BUILDER = ROOT / "scripts/build_magic_orb_design_readiness_v1.py"
SCREENSHOT = ROOT / "reports/magic_orb_design_screenshot_latest.png"
READINESS = ROOT / "reports/magic_orb_design_readiness_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--verdict",
        choices=("pass_open_beta_poc", "fail"),
        default="pass_open_beta_poc",
    )
    ap.add_argument("--notes-ko", default="")
    ap.add_argument("--skip-rebuild", action="store_true")
    args = ap.parse_args()

    commander_ok = args.verdict == "pass_open_beta_poc"
    doc = {
        "schema": "magic_orb_commander_visual_review_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "commander_visual_ok": commander_ok,
        "tier": "open_beta_poc" if commander_ok else "blocked",
        "screenshot": str(SCREENSHOT.relative_to(ROOT)).replace("\\", "/"),
        "notes_ko": args.notes_ko
        or (
            "오픈베타 POC 시각 통과 — 연구 라벨·빌더 경로 제거, Ask/Explore 분리, 1스크린 정보 밀도 개선. "
            "완성 제품·Track A 아님."
        ),
        "allowed_claims": [
            "engineering+design 자동 probe 통과",
            "오픈베타 관측 구 체험 가능",
        ],
        "disallowed_claims": [
            "소비자 제품 완성",
            "Track A 승격",
            "디자인 최종 완료",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_rebuild:
        flag = "true" if commander_ok else "false"
        proc = subprocess.run(
            [sys.executable, str(BUILDER), "--commander-visual-ok", flag],
            cwd=str(ROOT),
            check=False,
        )
        if proc.returncode != 0:
            return proc.returncode

    if READINESS.is_file():
        readiness = json.loads(READINESS.read_text(encoding="utf-8-sig"))
        print(
            json.dumps(
                {
                    "ok": True,
                    "commander_visual_ok": commander_ok,
                    "consumer_ready": readiness.get("consumer_ready"),
                    "design_ok": readiness.get("design_ok"),
                    "verdict_ko": readiness.get("verdict_ko"),
                },
                ensure_ascii=False,
            )
        )
    return 0 if commander_ok else 1


if __name__ == "__main__":
    sys.exit(main())
