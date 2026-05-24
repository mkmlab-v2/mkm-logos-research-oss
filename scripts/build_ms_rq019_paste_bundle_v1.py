#!/usr/bin/env python3
"""Concatenate MS RQ-019 paste_ready sections into one bundle for copy/paste."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE = ROOT / "reports/ms_rq019_paste_ready"
ORDER = [
    ("K1 문제", "k1_problem_paste.txt", True),
    ("K2 방법", "k2_method_paste.txt", True),
    ("K2 표(선택)", "k2_two_track_architecture_paste.txt", False),
    ("K3 차별", "k3_differentiation_paste.txt", True),
    ("면책", "disclaimer_footer_paste.txt", True),
    ("FinOps L1(선택)", "finops_l1_official_status_paste.txt", False),
    ("K3 Visual(선택)", "k3_visual_reasoning_path_appendix_paste.txt", False),
    ("K3 Logos(선택)", "k3_logos_chronology_modular_paste.txt", False),
    ("O-P5 한 줄", "op5_ms_paste_one_liner.txt", False),
]
OUT = PASTE / "00_all_paste_bundle.txt"
OUT_HWPX = PASTE / "hwpx_fact_lock_5blocks_v1.txt"
META = ROOT / "reports/ms_rq019_paste_bundle_latest.json"
# HWPX ms_microsoft_ma_jung_filled_v1 — SSOT paste only (00_paste_order steps 1–5 + 5b)
HWPX_ORDER = [
    ("1. K1 문제", "k1_problem_paste.txt"),
    ("2. K2 방법", "k2_method_paste.txt"),
    ("3. K3 차별", "k3_differentiation_paste.txt"),
    ("4. 부록 TECH MOAT", "technical_moat_sector_paste.txt"),
    ("5. 하단 면책", "disclaimer_footer_paste.txt"),
]


def main() -> int:
    lines: list[str] = [
        "# MS RQ-019 paste bundle (auto-generated — section headers for navigation only)",
        f"# generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "# Paste each section into the matching MS form field. Do not submit this file as one block.",
        "",
    ]
    sections: list[dict] = []
    missing: list[str] = []

    for title, fname, required in ORDER:
        path = PASTE / fname
        if not path.is_file():
            if required:
                missing.append(fname)
            continue
        body = path.read_text(encoding="utf-8").strip()
        lines.extend([f"===== {title} ({fname}) =====", body, ""])
        sections.append({"title": title, "file": fname, "chars": len(body), "required": required})

    if missing:
        print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False))
        return 1

    OUT.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    hwpx_lines: list[str] = [
        "# HWPX Fact-Lock paste (5 blocks) — copy each section into ms_microsoft_ma_jung_filled_v1.hwpx",
        f"# generated_at_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "# SSOT: reports/ms_rq019_paste_ready/*.txt — 금지: 100%, 무손실 완성, 47.1% 상용, 내부 json 경로",
        "",
    ]
    hwpx_sections: list[dict] = []
    for title, fname in HWPX_ORDER:
        path = PASTE / fname
        if not path.is_file():
            missing.append(fname)
            continue
        body = path.read_text(encoding="utf-8").strip()
        hwpx_lines.extend([f"===== {title} ({fname}) =====", body, ""])
        hwpx_sections.append({"title": title, "file": fname, "chars": len(body)})

    if not missing:
        OUT_HWPX.write_text("\n".join(hwpx_lines).strip() + "\n", encoding="utf-8")

    meta = {
        "schema": "ms_rq019_paste_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "out": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "hwpx_out": str(OUT_HWPX.relative_to(ROOT)).replace("\\", "/") if OUT_HWPX.is_file() else None,
        "sections": sections,
        "hwpx_sections": hwpx_sections,
        "assistant_html": "reports/demo/ms_rq019_paste_assistant_v1.html",
        "ok": True,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
