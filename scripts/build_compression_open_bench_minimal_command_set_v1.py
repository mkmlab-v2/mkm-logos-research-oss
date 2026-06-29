#!/usr/bin/env python3
"""10-minute open-bench Minimal Command Set draft for commander review [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json"
OUT_JSON = ROOT / "reports/compression_open_bench_minimal_command_set_v1_latest.json"
OUT_MD = ROOT / "reports/compression_open_bench_minimal_command_set_v1_latest.md"

COMMANDS = [
    {
        "step": 1,
        "title": "Clone + Python deps",
        "bash": "pip install -r requirements-public-reproduce.txt",
        "windows": "py -m pip install -r requirements-public-reproduce.txt",
        "minutes": 2,
    },
    {
        "step": 2,
        "title": "Evidence Lv1 chain (visitor smoke)",
        "bash": "python3 scripts/run_compression_evidence_lv1_chain_v1.py --skip-handoff",
        "windows": "py scripts/run_compression_evidence_lv1_chain_v1.py --skip-handoff",
        "minutes": 3,
    },
    {
        "step": 3,
        "title": "Open-bench onboard smoke",
        "bash": "python3 scripts/run_compression_open_bench_onboard_smoke_v1.py",
        "windows": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-CompressionOpenBenchOnboardSmoke_v1.ps1",
        "minutes": 3,
    },
    {
        "step": 4,
        "title": "Contributor JSONL validate (optional PR path)",
        "bash": "python3 scripts/validate_compression_contributor_jsonl_v1.py --jsonl data/compression/contributions/premium_cs_masked_open_bench_seed_v1.jsonl --min-rows 10",
        "windows": "py scripts/validate_compression_contributor_jsonl_v1.py --jsonl data/compression/contributions/premium_cs_masked_open_bench_seed_v1.jsonl --min-rows 10",
        "minutes": 2,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_md(doc: dict) -> str:
    lines = [
        "# Compression Open-Bench — Minimal Command Set (10 min) [DRAFT]",
        "",
        f"- Generated: {doc['generated_at_utc']}",
        "- **SEND_GATE: HOLD** · commander final approval required",
        "- **FAIL-COMP-004:** per-SKU metrics only; never merge Track A / ~47.5% headline",
        "",
        "## Windows (repo root)",
        "",
    ]
    for c in doc["commands"]:
        lines.extend([f"### Step {c['step']}: {c['title']} (~{c['minutes']} min)", "", "```powershell", c["windows"], "```", ""])
    lines.extend(
        [
            "## Enterprise apply (separate funnel · human Turnstile)",
            "",
            "- URL: https://app.jema-ai.com/enterprise/apply",
            "- API smoke: `py scripts/check_enterprise_apply_live_smoke_v1.py`",
            "",
            "## Forbidden",
            "",
        ]
    )
    for f in doc.get("forbidden") or []:
        lines.append(f"- {f}")
    lines.extend(["", "---", "Reproduce: `py scripts/build_compression_open_bench_minimal_command_set_v1.py`", ""])
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json-out", type=Path, default=OUT_JSON)
    ap.add_argument("--md-out", type=Path, default=OUT_MD)
    args = ap.parse_args()

    kit = {}
    if KIT.is_file():
        kit = json.loads(KIT.read_text(encoding="utf-8-sig"))
    doc = {
        "schema": "compression_open_bench_minimal_command_set_v1",
        "generated_at_utc": _utc(),
        "status": "draft_commander_review",
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "labels": ["DRAFT", "research_only", "[HYPO]", "contributor_provided"],
        "estimated_minutes": sum(c["minutes"] for c in COMMANDS),
        "commands": COMMANDS,
        "forbidden": kit.get("forbidden") or [],
        "kit_pointer": "docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json",
        "reproduce": "py scripts/build_compression_open_bench_minimal_command_set_v1.py",
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_out.write_text(render_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "minutes": doc["estimated_minutes"], "out": str(args.md_out.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
