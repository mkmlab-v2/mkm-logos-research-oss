#!/usr/bin/env python3
"""Pre-export gates for OpenData 327 submission parts B/C (local, no network)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PART_B = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md"
PART_C = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_submission_v1.md"
DEFAULT_OUT = ROOT / "reports/opendata_327_pre_export_gates_latest.json"

G1_PATTERNS = [
    re.compile(r"47\s*%", re.I),
    re.compile(r"\b0\.47\b"),
    re.compile(r"compression\s+47", re.I),
    re.compile(r"Safety\s+PLC", re.I),
    re.compile(r"OEM\s+royalty", re.I),
    re.compile(r"per-device", re.I),
    re.compile(r"hallucination[- ]free", re.I),
    re.compile(r"live\s+trading", re.I),
    re.compile(r"실매매", re.I),
]

G4_POSITIVE = [
    re.compile(r"LG.*검증\s*완료"),
    re.compile(r"최종\s*선정(?!.*기재하지)"),
    re.compile(r"PoC\s*완료", re.I),
    re.compile(r"양산\s*적용\s*완료"),
    re.compile(r"2차\s*평가\s*통과"),
]
G4_NEGATION_MARKERS = ("기재하지 않음", "미기재", "주장하지", "없음")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scan(path: Path, patterns: list[re.Pattern[str]]) -> list[dict[str, str]]:
    if not path.is_file():
        return [{"pattern": "missing_file", "line": 0, "excerpt": str(path)}]
    hits: list[dict[str, str]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for pat in patterns:
            if pat.search(line):
                hits.append({"pattern": pat.pattern, "line": i, "excerpt": line.strip()[:200]})
    return hits


def build() -> dict[str, Any]:
    g1_b = _scan(PART_B, G1_PATTERNS)
    g1_c = _scan(PART_C, G1_PATTERNS)
    g4_raw = _scan(PART_B, G4_POSITIVE)
    g4 = [h for h in g4_raw if not any(m in h["excerpt"] for m in G4_NEGATION_MARKERS)]
    gates = [
        {"id": "G1_B", "ok": len(g1_b) == 0, "hits": g1_b},
        {"id": "G1_C", "ok": len(g1_c) == 0, "hits": g1_c},
        {"id": "G4", "ok": len(g4) == 0, "hits": g4},
    ]
    all_ok = all(g["ok"] for g in gates)
    return {
        "schema": "opendata_327_pre_export_gates_v1",
        "generated_at_utc": _utc_now(),
        "all_gates_ok_for_export_draft": all_ok,
        "gates": gates,
        "sources": {
            "part_b_md": PART_B.relative_to(ROOT).as_posix(),
            "part_c_md": PART_C.relative_to(ROOT).as_posix(),
        },
        "merge_guide": "docs/final/artifacts/opendata_327_submission_pdf_merge_guide_v1_latest.md",
        "next_human": [
            "K-Startup 표지(A) 양식 수동 병합 + Annex(D) 선택",
            "§2-2 목표안 수치는 제출 전 내부 벤치로 확정",
            "K-Startup + 나라장터 접수 (6/5 18:00)",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_gates_ok_for_export_draft"], "output": str(args.out_json)}, ensure_ascii=False))
    return 0 if doc["all_gates_ok_for_export_draft"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
