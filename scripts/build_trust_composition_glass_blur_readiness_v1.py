#!/usr/bin/env python3
"""Merge glass/blur gate + Playwright A/B capture → readiness SSOT."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/trust_composition_glass_blur_readiness_v1_latest.json"
GATE = ROOT / "reports/trust_composition_glass_blur_gate_v1_latest.json"
PLAYWRIGHT = ROOT / "reports/trust_composition_glass_blur_playwright_v1_latest.json"
COMMANDER = ROOT / "reports/trust_composition_glass_blur_commander_visual_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(
    *,
    gate_doc: dict[str, Any] | None,
    pw_doc: dict[str, Any] | None,
    commander_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    gate_ok = bool(gate_doc and gate_doc.get("ok") and gate_doc.get("decision") == "PASS")
    capture_ok = bool(pw_doc and pw_doc.get("capture_ok") and not pw_doc.get("skipped"))
    commander_ok = bool(commander_doc and commander_doc.get("commander_visual_ok"))
    ab_verdict = (commander_doc or {}).get("ab_verdict", "pending")

    if not gate_ok:
        verdict = "gate 미통과 — A/B 기록 금지"
    elif not capture_ok:
        verdict = "Playwright A/B 캡처 대기"
    elif not commander_ok:
        verdict = "A/B 캡처 OK · commander visual 대기"
    elif ab_verdict == "prefer_flat_baseline":
        verdict = "flat baseline 채택 · glass clinic LOI 기본 적용 금지"
    else:
        verdict = f"commander verdict: {ab_verdict}"

    experiment_ready = gate_ok and capture_ok and commander_ok

    return {
        "schema": "trust_composition_glass_blur_readiness_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "lane_status": "research_only",
        "not_clinic_loi_default": True,
        "gate_ok": gate_ok,
        "capture_ok": capture_ok,
        "commander_visual_ok": commander_ok,
        "ab_verdict": ab_verdict,
        "experiment_ready": experiment_ready,
        "glass_promotion": (commander_doc or {}).get("glass_promotion", "deferred"),
        "clinic_loi_default_surface": (commander_doc or {}).get("clinic_loi_default", "flat"),
        "verdict_ko": verdict,
        "artifacts": {
            "gate": str(GATE.relative_to(ROOT)).replace("\\", "/"),
            "playwright": str(PLAYWRIGHT.relative_to(ROOT)).replace("\\", "/"),
            "commander": str(COMMANDER.relative_to(ROOT)).replace("\\", "/"),
            "screenshots": (pw_doc or {}).get("screenshots"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build(
        gate_doc=_read(GATE),
        pw_doc=_read(PLAYWRIGHT),
        commander_doc=_read(COMMANDER),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "experiment_ready": doc["experiment_ready"],
                "ab_verdict": doc["ab_verdict"],
                "verdict_ko": doc["verdict_ko"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
