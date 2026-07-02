#!/usr/bin/env python3
"""Logos Inquiry product completion DoD — Shipped vs Product-ready (design + quality + beta).

Aggregates disk SSOT only; does not replace live battery or legal review.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_inquiry_product_completion_dod_v1_latest.json"
OUT_MD = ROOT / "reports/logos_inquiry_product_completion_dod_v1_latest.md"

QUALITY_BUNDLE = ROOT / "reports/logos_ask_quality_bundle_v1_latest.json"
BETA_GATE = ROOT / "docs/final/artifacts/logos_oss_beta_recruitment_gate_v1_latest.json"
BETA_CONTRACT = ROOT / "docs/final/artifacts/logos_inquiry_beta_v1_latest.json"
COMMERCIAL = ROOT / "docs/final/artifacts/logos_research_commercial_product_v1_latest.json"
GAP_BOARD = ROOT / "reports/logos_ask_gap_board_v1_latest.md"

UI_COMPONENTS: list[tuple[str, str, str]] = [
    ("ask_page", "projects/no1kmedi/src/app/logos-research/ask/page.tsx", "P0"),
    ("ask_client", "projects/no1kmedi/src/components/logos-research/LogosResearchAskClient.tsx", "P0"),
    ("ask_onboarding", "projects/no1kmedi/src/components/logos-research/LogosResearchAskOnboarding.tsx", "P0"),
    ("ask_quota_bar", "projects/no1kmedi/src/components/logos-research/LogosResearchAskQuotaBar.tsx", "P0"),
    ("ask_post_feedback", "projects/no1kmedi/src/components/logos-research/LogosResearchAskPostFeedbackStrip.tsx", "P0"),
    ("ask_citation_lock_strip", "projects/no1kmedi/src/components/logos-research/LogosResearchAskCitationLockStrip.tsx", "P0"),
    ("ask_display_lib", "projects/no1kmedi/src/lib/logosInquiryAskDisplayV1.ts", "P0"),
    ("beta_strip", "projects/no1kmedi/src/components/logos-research/LogosResearchBetaStrip.tsx", "P1"),
    ("copy_json", "projects/no1kmedi/marketing-site/logos-research-copy.json", "P0"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _ui_checks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component_id, rel, tier in UI_COMPONENTS:
        p = ROOT / rel.replace("/", "\\") if "\\" in str(ROOT) else ROOT / rel
        p = ROOT / rel
        rows.append(
            {
                "id": component_id,
                "path": rel.replace("\\", "/"),
                "tier": tier,
                "exists": p.is_file(),
            }
        )
    return rows


def _gaps(
    *,
    quality: dict[str, Any],
    beta_gate: dict[str, Any],
    beta_contract: dict[str, Any],
    ui_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    if not quality.get("completion_ok"):
        gaps.append(
            {
                "id": "quality_completion",
                "severity": "P0",
                "fix": "py scripts/run_logos_ask_quality_bundle_v1.py --live-external",
            }
        )
    if not beta_gate.get("ok"):
        gaps.append(
            {
                "id": "beta_recruitment_gate",
                "severity": "P0",
                "fix": "py scripts/check_logos_oss_beta_recruitment_gate_v1.py",
            }
        )
    payment = (beta_contract.get("payment") or {}) if isinstance(beta_contract.get("payment"), dict) else {}
    if payment.get("status") != "deferred":
        gaps.append(
            {
                "id": "payment_not_deferred",
                "severity": "P1",
                "note": "Expected deferred until post-OSS verification",
            }
        )
    studio = beta_contract.get("graphics_studio") or {}
    if isinstance(studio, dict) and studio.get("status") != "deferred":
        gaps.append({"id": "studio_not_deferred", "severity": "P2"})
    for row in ui_rows:
        if not row.get("exists"):
            gaps.append(
                {
                    "id": f"ui_missing_{row['id']}",
                    "severity": row.get("tier", "P1"),
                    "path": row.get("path"),
                }
            )
    longtail = (quality.get("gates") or {}).get("longtail_in_quality_gate")
    if longtail is False:
        gaps.append(
            {
                "id": "longtail_not_in_p0_gate",
                "severity": "P2",
                "note": "By design — expand Hub coverage before promoting longtail to gate",
            }
        )
    return gaps


def build_report() -> dict[str, Any]:
    quality = _read_json(QUALITY_BUNDLE)
    beta_gate = _read_json(BETA_GATE)
    beta_contract = _read_json(BETA_CONTRACT)
    commercial = _read_json(COMMERCIAL)
    ui_rows = _ui_checks()
    ui_ok = all(r["exists"] for r in ui_rows if r["tier"] == "P0")
    gaps = _gaps(
        quality=quality,
        beta_gate=beta_gate,
        beta_contract=beta_contract,
        ui_rows=ui_rows,
    )
    p0_gaps = [g for g in gaps if g.get("severity") == "P0"]
    product_p0_ok = (
        bool(quality.get("completion_ok"))
        and bool(beta_gate.get("ok"))
        and ui_ok
        and not p0_gaps
    )
    return {
        "schema": "logos_inquiry_product_completion_dod_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "product_p0_ok": product_p0_ok,
        "promotion_to_a_track_allowed": False,
        "layers": {
            "quality": {
                "completion_ok": quality.get("completion_ok"),
                "shipped_ok": quality.get("shipped_ok"),
                "quality_ok": quality.get("quality_ok"),
                "artifact": str(QUALITY_BUNDLE.relative_to(ROOT)).replace("\\", "/"),
            },
            "beta_gate": {
                "ok": beta_gate.get("ok"),
                "recruitment_ready": beta_gate.get("recruitment_ready"),
                "blockers": beta_gate.get("blockers") or [],
                "artifact": str(BETA_GATE.relative_to(ROOT)).replace("\\", "/"),
            },
            "beta_contract": {
                "payment_status": (beta_contract.get("payment") or {}).get("status"),
                "studio_status": (beta_contract.get("graphics_studio") or {}).get("status"),
                "surface": beta_contract.get("surface_primary"),
                "artifact": str(BETA_CONTRACT.relative_to(ROOT)).replace("\\", "/"),
            },
            "commercial_product": {
                "domain": commercial.get("public_domain"),
                "artifact": str(COMMERCIAL.relative_to(ROOT)).replace("\\", "/"),
            },
            "ui_components": ui_rows,
        },
        "gaps": gaps,
        "gap_board_ref": str(GAP_BOARD.relative_to(ROOT)).replace("\\", "/") if GAP_BOARD.is_file() else None,
        "reproduce_quality": "py scripts/run_logos_ask_quality_bundle_v1.py --live-external",
        "reproduce": "py scripts/build_logos_inquiry_product_completion_dod_v1.py",
        "next_ms_lane_note_ko": "결제·grant SEND는 Product P0 밖 — prophecy/compression은 JEMA OS guest slot (별 채팅)",
    }


def _write_md(report: dict[str, Any]) -> None:
    lines = [
        "# Logos Inquiry Product Completion DoD v1",
        "",
        f"generated_at_utc: {report.get('generated_at_utc')}",
        f"product_p0_ok: **{report.get('product_p0_ok')}** · send_gate: **HOLD**",
        "",
        "## Layers",
        "",
        "| Layer | OK | SSOT |",
        "|-------|-----|------|",
    ]
    q = report.get("layers", {}).get("quality", {})
    b = report.get("layers", {}).get("beta_gate", {})
    lines.append(f"| Quality completion | {q.get('completion_ok')} | `{q.get('artifact')}` |")
    lines.append(f"| Beta recruitment gate | {b.get('ok')} | `{b.get('artifact')}` |")
    lines.append("")
    lines.append("## P0 UI components")
    lines.append("")
    for row in report.get("layers", {}).get("ui_components") or []:
        mark = "✓" if row.get("exists") else "✗"
        lines.append(f"- [{mark}] `{row.get('path')}` ({row.get('tier')})")
    lines.append("")
    if report.get("gaps"):
        lines.append("## Gaps")
        lines.append("")
        for g in report["gaps"]:
            lines.append(f"- **{g.get('id')}** ({g.get('severity')}): {g.get('fix') or g.get('note') or g.get('path')}")
        lines.append("")
    lines.append(f"Reproduce: `{report.get('reproduce')}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--write-md", action="store_true", default=True)
    args = ap.parse_args()
    report = build_report()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        _write_md(report)
    print(
        json.dumps(
            {
                "ok": True,
                "product_p0_ok": report["product_p0_ok"],
                "gaps": len(report["gaps"]),
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["product_p0_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
