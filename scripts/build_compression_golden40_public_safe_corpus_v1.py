#!/usr/bin/env python3
"""Export first 40 public-safe eval texts from MULTILENS_PERFORMANCE_EVAL_INPUT_V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL_IN = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
OUT_JSONL = ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
OUT_MANIFEST = ROOT / "docs/final/artifacts/compression_golden40_public_safe_corpus_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(*, max_cases: int = 40) -> dict[str, Any]:
    if not EVAL_IN.is_file():
        return {"ok": False, "error": f"missing {EVAL_IN}"}
    doc = json.loads(EVAL_IN.read_text(encoding="utf-8-sig"))
    cases = list(doc.get("compression_cases") or [])[:max_cases]
    rows: list[dict[str, Any]] = []
    for case in cases:
        raw = case.get("raw_text")
        if not isinstance(raw, str) or not raw.strip():
            continue
        rows.append(
            {
                "id": case.get("id") or f"golden40-{len(rows):03d}",
                "source": "multilens_performance_eval_input_v2_public_safe",
                "domain_tag": "en-ops-bench",
                "text": raw.strip(),
                "public_safe": True,
                "forbidden_as_customer_sla": True,
            }
        )
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "compression_golden40_public_safe_corpus_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "source_eval_input": EVAL_IN.relative_to(ROOT).as_posix(),
        "corpus_path": OUT_JSONL.relative_to(ROOT).as_posix(),
        "sha256": _sha256(OUT_JSONL),
        "case_count": len(rows),
        "ok": len(rows) == max_cases,
        "boundary_ack": (
            "Synthetic EN ops bench excerpts only; internal regression reference — "
            "not customer SLA or press headline."
        ),
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-cases", type=int, default=40)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    doc = build(max_cases=args.max_cases)
    print(json.dumps({"ok": doc.get("ok"), "case_count": doc.get("case_count")}, ensure_ascii=False))
    if args.strict and not doc.get("ok"):
        return 1
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
