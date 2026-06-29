#!/usr/bin/env python3
"""Validate nextgen LTM research slot files and emit status JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / "docs/research/nextgen_ltm_knowledge_os"
INDEX = SLOT / "INDEX.json"
OUT = ROOT / "reports/nextgen_ltm_research_slot_v1_latest.json"

REQUIRED = [
    "INDEX.json",
    "NEXTGEN_LTM_KNOWLEDGE_OS_WHITEPAPER_HYPO_V1.md",
    "NEXTGEN_LTM_KNOWLEDGE_OS_FACT_ONEPAGER_V1.md",
    "FACT_HYPO_ROADMAP_MATRIX_V1.md",
]

# Forbidden as FACT in the internal one-pager (counsel-safe)
FACT_FORBIDDEN = re.compile(
    r"TEE|SGX|TDX|Merkle|242\s*[×x]|Word Room|독점|선행기술\s*감사\s*완료",
    re.I,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    missing: list[str] = []
    files: list[dict[str, Any]] = []
    for name in REQUIRED:
        path = SLOT / name
        ok = path.is_file()
        if not ok:
            missing.append(name)
        files.append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "ok": ok,
                "bytes": path.stat().st_size if ok else 0,
            }
        )

    fact_path = SLOT / "NEXTGEN_LTM_KNOWLEDGE_OS_FACT_ONEPAGER_V1.md"
    fact_scan_ok = True
    fact_hits: list[str] = []
    if fact_path.is_file():
        text = fact_path.read_text(encoding="utf-8")
        # Section 5 lists forbidden topics explicitly — scan body only.
        scan_body = text.split("## 5.", 1)[0]
        for m in FACT_FORBIDDEN.finditer(scan_body):
            fact_hits.append(m.group(0))
        fact_scan_ok = not fact_hits

    index_ok = INDEX.is_file()
    slot_meta: dict[str, Any] = {}
    if index_ok:
        try:
            slot_meta = json.loads(INDEX.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            index_ok = False

    prior_art_path = SLOT / "PRIOR_ART_SEARCH_LOG.jsonl"
    prior_art_rows = 0
    if prior_art_path.is_file():
        prior_art_rows = sum(
            1 for ln in prior_art_path.read_text(encoding="utf-8").splitlines() if ln.strip()
        )
    prior_art_ok = prior_art_rows >= 4

    ok = not missing and index_ok and fact_scan_ok and prior_art_ok
    report: dict[str, Any] = {
        "schema": "nextgen_ltm_research_slot_v1",
        "generated_at_utc": _utc(),
        "classification": "[HYPO] · research_only",
        "send_gate": "HOLD",
        "slot_id": slot_meta.get("slot_id", "nextgen_ltm_knowledge_os"),
        "files": files,
        "missing": missing,
        "fact_onepager_forbidden_hits": fact_hits,
        "prior_art_log_rows": prior_art_rows,
        "prior_art_log_ok": prior_art_ok,
        "ok": ok,
        "reproduce": "py scripts/build_nextgen_ltm_research_slot_v1.py",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out_json.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
