#!/usr/bin/env python3
"""Grep part B/C submission MDs for OpenData 327 forbidden phrases (local)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = [
    ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md",
    ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_submission_v1.md",
]
OVERVIEW = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md"
FORBIDDEN_SUBMISSION = [
    re.compile(r"47\s*%", re.I),
    re.compile(r"Safety\s+PLC", re.I),
    re.compile(r"hallucination[- ]free", re.I),
    re.compile(r"실매매"),
    re.compile(r"Track\s+A", re.I),
]
FORBIDDEN_OVERVIEW = FORBIDDEN_SUBMISSION + [
    re.compile(r"\b0\.47\b"),
    re.compile(r"\bLG\b"),
    re.compile(r"compression", re.I),
]
SHIPPED_CLAIMS = [
    re.compile(r"이미\s*구축\s*완료"),
    re.compile(r"상용\s*배포\s*완료"),
    re.compile(r"구현\s*완료"),
]
FAKE_PATENT = re.compile(r"출원번호\s*[:：]\s*\d{2,}")
NEGATION_MARKERS = (
    "기재하지 않음",
    "미기재",
    "합선하지",
    "합선 기재",
    "주장하지",
    "없음",
    "금지",
    "분리",
    "별 트랙",
    "격벽",
    "합선 출력 금지",
    "미합선",
)


def _line_excluded(line: str) -> bool:
    return any(m in line for m in NEGATION_MARKERS)


def _scan(path: Path, patterns: list[re.Pattern[str]]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    if not path.is_file():
        return [{"file": str(path), "error": "missing"}]
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if _line_excluded(line):
            continue
        for pat in patterns:
            if pat.search(line):
                hits.append({"file": path.name, "line": i, "pattern": pat.pattern, "excerpt": line[:160]})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("submission", "overview", "shipped", "tech"), default="submission")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/opendata_327_forbidden_grep_latest.json")
    args = ap.parse_args()

    if args.mode == "submission":
        hits: list[dict[str, object]] = []
        for p in PATHS:
            hits.extend(_scan(p, FORBIDDEN_SUBMISSION))
    elif args.mode == "overview":
        hits = _scan(OVERVIEW, FORBIDDEN_OVERVIEW)
    elif args.mode == "shipped":
        hits = _scan(OVERVIEW, SHIPPED_CLAIMS)
    else:
        tech = ROOT / "docs/final/B2G_TECH_DISCLOSURE_ONEPAGER_PREP_V1.md"
        hits = []
        if not tech.is_file():
            hits.append({"file": str(tech), "error": "missing"})
        elif FAKE_PATENT.search(tech.read_text(encoding="utf-8")):
            hits.append({"file": tech.name, "error": "fake_patent_number_pattern"})

    ok = len(hits) == 0
    doc = {
        "schema": "opendata_327_forbidden_grep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": args.mode,
        "ok": ok,
        "hits": hits,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "hits": len(hits)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
