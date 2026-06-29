#!/usr/bin/env python3
"""Pre-counsel copy guardrail scan for Logos GTM LinkedIn/B2B variants (no auto-edit)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_gtm_linkedin_b2b_copy_scan_v1_latest.json"

SCAN_PATH = "docs/final/artifacts/logos_gtm_linkedin_b2b_copy_variants_v1_latest.md"

NEGATION_MARKERS = (
    "do not",
    "does not",
    "하지 않",
    "아닌",
    "금지",
    "forbidden",
    "제외",
    "미포함",
    "쓰지 말",
    "not ",
    "no buy/sell",
    "not investment",
)

FORBIDDEN_SECTION_HEADERS = re.compile(
    r"^##\s+(Forbidden|금지)",
    re.I,
)

RULES: list[dict[str, Any]] = [
    {
        "id": "prophecy_hit_rate_marketing",
        "pattern": re.compile(r"router_hit_rate|적중률\s*[○0-9]|hit\s*rate\s*[○0-9]|예언\s*적중", re.I),
        "severity": "block",
    },
    {
        "id": "thermo_alias_fact",
        "pattern": re.compile(r"\$E_i|\$P_f|\$D_d|\$H_c|γ\s*동적|gamma\s*transition", re.I),
        "severity": "block",
    },
    {
        "id": "external_send_true",
        "pattern": re.compile(r"ready_for_external_send:\s*`?true", re.I),
        "severity": "block",
    },
    {
        "id": "guaranteed_returns",
        "pattern": re.compile(r"guaranteed\s+returns|수익\s*보장|always\s+profitable", re.I),
        "severity": "block",
    },
    {
        "id": "toe_complete",
        "pattern": re.compile(r"TOE\s*완성|만물예측\s*완성|75식\s*전부\s*상용", re.I),
        "severity": "block",
    },
    {
        "id": "live_trading_go",
        "pattern": re.compile(r"live\s+trading\s+GO|실매매\s*트리거", re.I),
        "severity": "block",
    },
    {
        "id": "competitor_absolute",
        "pattern": re.compile(r"ChatGPT.*(항상|always).*(틀|wrong|hallucin)", re.I),
        "severity": "block",
    },
]

REQUIRED_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("send_gate_hold", re.compile(r"send_gate:\s*HOLD", re.I)),
    ("external_send_false", re.compile(r"ready_for_external_send:\s*`?false", re.I)),
    ("non_gating", re.compile(r"\[NON_GATING\]|NON_GATING", re.I)),
    ("not_investment_advice", re.compile(r"Not investment advice|투자.*아님|투자·치료", re.I)),
    ("demo_url", re.compile(r"api\.jemaai\.cloud/public_showroom_meaning_topology_qa_v2", re.I)),
    ("internal_draft", re.compile(r"INTERNAL_DRAFT|DRAFT_AUTO", re.I)),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _forbidden_section_lines(lines: list[str]) -> set[int]:
    blocked: set[int] = set()
    in_section = False
    for i, line in enumerate(lines):
        if FORBIDDEN_SECTION_HEADERS.match(line.strip()):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            in_section = False
            continue
        if in_section and line.strip():
            blocked.add(i + 1)
    return blocked


def _line_negated(line: str) -> bool:
    lower = line.lower()
    return any(m.lower() in lower for m in NEGATION_MARKERS)


def _scan_file(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.is_file():
        return {"path": rel, "ok": False, "missing": True, "hits": [], "missing_markers": []}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    forbidden_section = _forbidden_section_lines(lines)
    hits: list[dict[str, Any]] = []

    missing_markers = [
        name for name, pat in REQUIRED_MARKERS if not pat.search(text)
    ]
    if missing_markers:
        hits.append(
            {
                "rule_id": "required_markers",
                "severity": "block",
                "message": f"missing: {missing_markers}",
            }
        )

    for rule in RULES:
        for i, line in enumerate(lines, start=1):
            if not rule["pattern"].search(line):
                continue
            if i in forbidden_section:
                continue
            if _line_negated(line):
                continue
            hits.append(
                {
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "line": i,
                    "excerpt": line.strip()[:200],
                }
            )

    blocking = [h for h in hits if h.get("severity") == "block"]
    return {
        "path": rel,
        "ok": not blocking,
        "missing": False,
        "hits": hits,
        "missing_markers": missing_markers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--path",
        default=SCAN_PATH,
        help="Relative path to copy variants markdown",
    )
    args = parser.parse_args()

    result = _scan_file(args.path)
    scan_ok = result.get("ok") and not result.get("missing")

    report = {
        "schema": "logos_gtm_linkedin_b2b_copy_scan_v1",
        "generated_at_utc": _utc_now(),
        "scan_ok": scan_ok,
        "ready_for_counsel_submission": scan_ok,
        "ready_for_external_send": False,
        "send_gate": "HOLD",
        "boundary_ack": "Automated pre-counsel scan only; not legal sign-off.",
        "file": result,
        "reproduce": "py scripts/check_logos_gtm_linkedin_b2b_copy_scan_v1.py",
    }

    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": scan_ok, "out": str(out_path.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if scan_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
