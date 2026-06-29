#!/usr/bin/env python3
"""Record commander visual A/B review for glass/blur experiment.

Default verdict: prefer_flat_baseline — 70s clinic LOI keeps flat; glass stays deferred.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/trust_composition_glass_blur_commander_visual_v1_latest.json"
BUILDER = ROOT / "scripts/build_trust_composition_glass_blur_readiness_v1.py"
PLAYWRIGHT_JSON = ROOT / "reports/trust_composition_glass_blur_playwright_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--verdict",
        choices=("prefer_flat_baseline", "glass_ok_hub_only", "fail"),
        default="prefer_flat_baseline",
    )
    ap.add_argument("--notes-ko", default="")
    ap.add_argument("--skip-rebuild", action="store_true")
    args = ap.parse_args()

    commander_ok = args.verdict != "fail"
    pw = {}
    if PLAYWRIGHT_JSON.is_file():
        pw = json.loads(PLAYWRIGHT_JSON.read_text(encoding="utf-8-sig"))

    glass_promotion = "deferred"
    clinic_default = "flat"
    if args.verdict == "glass_ok_hub_only":
        glass_promotion = "hub_experiment_only"
        clinic_default = "flat"
    elif args.verdict == "prefer_flat_baseline":
        glass_promotion = "deferred"
        clinic_default = "flat"
    else:
        glass_promotion = "blocked"
        clinic_default = "flat"

    doc = {
        "schema": "trust_composition_glass_blur_commander_visual_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "commander_visual_ok": commander_ok,
        "ab_verdict": args.verdict,
        "clinic_loi_default": clinic_default,
        "glass_promotion": glass_promotion,
        "screenshots": pw.get("screenshots"),
        "notes_ko": args.notes_ko
        or (
            "A/B: flat=clinic LOI baseline 유지 · glass=연구 전용(70대 가독성·blur cap). "
            "clinic LOI·외부 송출 기본 적용 금지."
        ),
        "allowed_claims": [
            "flat baseline gate PASS",
            "glass blur experiment 내부 preview",
            "hub/mkmlife 실험 브랜치 후보만",
        ],
        "disallowed_claims": [
            "clinic LOI glass 기본 적용",
            "디자인 최종 완료",
            "Track A 승격",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_rebuild:
        proc = subprocess.run([sys.executable, str(BUILDER)], cwd=str(ROOT), check=False)
        if proc.returncode != 0:
            return proc.returncode

    print(
        json.dumps(
            {
                "ok": commander_ok,
                "ab_verdict": args.verdict,
                "glass_promotion": glass_promotion,
                "clinic_loi_default": clinic_default,
            },
            ensure_ascii=False,
        )
    )
    return 0 if commander_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
