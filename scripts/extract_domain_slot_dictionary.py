#!/usr/bin/env python3
"""Build a domain slot dictionary from input corpus tokens."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_DOMAIN_SLOT_DICTIONARY_V6.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+")
STOP = {
    "the",
    "and",
    "or",
    "is",
    "are",
    "to",
    "of",
    "a",
    "in",
    "for",
    "with",
    "this",
    "that",
    "on",
    "by",
    "be",
    "as",
    "it",
    "when",
    "can",
    "must",
    "하지",
    "해야",
    "한다",
    "수",
    "있는",
}


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in TOKEN_RE.findall(text)]


def main() -> int:
    doc = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    texts = [str(c.get("raw_text", "")) for c in doc.get("compression_cases", [])]
    freq = Counter()
    for t in texts:
        for w in _tokens(t):
            if len(w) <= 1 or w in STOP:
                continue
            freq[w] += 1

    top = [w for w, _ in freq.most_common(120)]
    groups = {
        "state": [w for w in top if any(k in w for k in ("state", "명리", "전이", "regime"))][:20],
        "policy": [w for w in top if any(k in w for k in ("policy", "gate", "boundary", "trigger", "감사", "검사"))][:20],
        "evidence": [w for w in top if any(k in w for k in ("evidence", "witness", "trace", "증거", "원문", "해시"))][:20],
        "manual": [w for w in top if any(k in w for k in ("manual", "strict", "review", "수동", "엄격", "검토"))][:20],
        "sasang": [w for w in top if any(k in w for k in ("체질", "사상의학", "sasang", "소양", "소음", "태양", "태음"))][:20],
        "bible": [w for w in top if any(k in w for k in ("bible", "logos", "성경", "시편", "원어"))][:20],
        "ops": [w for w in top if any(k in w for k in ("compression", "복원", "token", "fidelity", "jaccard", "saving"))][:20],
    }
    # backfill sparse groups from remaining high-freq tokens
    remain = [w for w in top if all(w not in v for v in groups.values())]
    for g in groups:
        while len(groups[g]) < 8 and remain:
            groups[g].append(remain.pop(0))

    out = {
        "schema": "multilens_domain_slot_dictionary_v6",
        "source_input": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        "slots": {
            "S1": groups["state"],
            "S2": groups["policy"],
            "S3": groups["evidence"],
            "S4": groups["manual"],
            "S5": groups["sasang"],
            "S6": groups["bible"],
            "S7": groups["ops"],
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
