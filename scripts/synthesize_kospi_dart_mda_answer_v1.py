#!/usr/bin/env python3
"""Deterministic MD&A answer synthesis with paragraph citation lock.

Reproduce:
  py scripts/synthesize_kospi_dart_mda_answer_v1.py --query "연구개발비 증가 이유" --corpus docs/final/artifacts/kospi_dart_mda_corpus_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_poc_lib_v1 import (  # noqa: E402
    build_deterministic_answer,
    is_scope_violation_query,
    scope_refusal_payload,
)

DEFAULT_CORPUS = ROOT / "docs/final/artifacts/kospi_dart_mda_corpus_v1_latest.json"


def synthesize(query: str, corpus: dict[str, object]) -> dict[str, object]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}
    if is_scope_violation_query(q):
        return scope_refusal_payload(q)
    return build_deterministic_answer(q, corpus)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = ap.parse_args()

    if not args.corpus.is_file():
        print(json.dumps({"ok": False, "error": "missing_corpus", "path": str(args.corpus)}, ensure_ascii=False))
        return 1

    corpus = json.loads(args.corpus.read_text(encoding="utf-8-sig"))
    out = synthesize(args.query, corpus)
    print(json.dumps(out, ensure_ascii=False))
    if not out.get("ok"):
        return 0
    if out.get("citation_valid") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
