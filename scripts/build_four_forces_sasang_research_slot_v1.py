#!/usr/bin/env python3
"""Validate four-forces / sasang research slot and lexicon SSOT alignment."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / "docs/research/four_forces_sasang_biophysical"
LEXICON = ROOT / "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json"
OUT = ROOT / "reports/four_forces_sasang_research_slot_v1_latest.json"

REQUIRED = [
    "INDEX.json",
    "FOUR_FORCES_SASANG_WHITEPAPER_HYPO_V1.md",
    "FOUR_FORCES_SASANG_FACT_ONEPAGER_V1.md",
    "FACT_HYPO_ROADMAP_MATRIX_V1.md",
    "LEXICON_ALIGNMENT_MATRIX_V1.md",
]

FACT_FORBIDDEN = re.compile(
    r"세계\s*최(초|유)|전\s*세계\s*유일|실측\s*증명|Biophysical\s*Isomorphism.*FACT|TOE\s*완성|만물이론\s*완성",
    re.I,
)

# Whitepaper must not reintroduce draft EM/weak swap as SSOT
WHITEPAPER_SWAP_BAD = re.compile(
    r"전자기력.*소음인|약력.*소양인|em_force.*soeum|weak_force.*soyang",
    re.I,
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_lexicon() -> dict[str, Any]:
    return json.loads(LEXICON.read_text(encoding="utf-8-sig"))


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

    fact_path = SLOT / "FOUR_FORCES_SASANG_FACT_ONEPAGER_V1.md"
    fact_hits: list[str] = []
    if fact_path.is_file():
        scan_body = fact_path.read_text(encoding="utf-8").split("## 5.", 1)[0]
        fact_hits = [m.group(0) for m in FACT_FORBIDDEN.finditer(scan_body)]

    white_path = SLOT / "FOUR_FORCES_SASANG_WHITEPAPER_HYPO_V1.md"
    white_swap_hits: list[str] = []
    if white_path.is_file():
        wtext = white_path.read_text(encoding="utf-8")
        for m in WHITEPAPER_SWAP_BAD.finditer(wtext):
            ctx = wtext[max(0, m.start() - 80) : m.end() + 40]
            if "DRAFT_MISMATCH" in ctx or "스왑" in ctx or "오류" in ctx:
                continue
            white_swap_hits.append(m.group(0)[:60])

    lexicon_ok = LEXICON.is_file()
    lexicon_entries: list[dict[str, str]] = []
    if lexicon_ok:
        lex = _load_lexicon()
        for e in lex.get("entries") or []:
            if isinstance(e, dict):
                lexicon_entries.append(
                    {
                        "force_id": str(e.get("force_id", "")),
                        "sasang": str(e.get("sasang_label_ko", "")),
                    }
                )

    index_ok = (SLOT / "INDEX.json").is_file()
    ok = (
        not missing
        and index_ok
        and lexicon_ok
        and not fact_hits
        and not white_swap_hits
    )

    report: dict[str, Any] = {
        "schema": "four_forces_sasang_research_slot_v1",
        "generated_at_utc": _utc(),
        "classification": "[HYPO] · pedagogical_isomorphism_only",
        "send_gate": "HOLD",
        "slot_id": "four_forces_sasang_biophysical",
        "lexicon_ssot": str(LEXICON.relative_to(ROOT)).replace("\\", "/"),
        "lexicon_entries": lexicon_entries,
        "draft_mismatch_note": "EM↔Weak swap in commander draft — see LEXICON_ALIGNMENT_MATRIX_V1.md",
        "files": files,
        "missing": missing,
        "fact_onepager_forbidden_hits": fact_hits,
        "whitepaper_draft_swap_hits": white_swap_hits,
        "ok": ok,
        "reproduce": "py scripts/build_four_forces_sasang_research_slot_v1.py",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(args.out_json.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
