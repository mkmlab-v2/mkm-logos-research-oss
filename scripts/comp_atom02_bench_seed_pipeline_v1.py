#!/usr/bin/env python3
"""COMP-ATOM-02: seed genesis codebook from V2 bench tokens + re-run pointer router."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z]{3,}", text.lower()))


def main() -> int:
    inp = json.loads(INPUT_V2.read_text(encoding="utf-8"))
    cases = inp.get("compression_cases") or []
    cnt: Counter[str] = Counter()
    for c in cases:
        for w in _tokens(str(c.get("raw_text", ""))):
            cnt[w] += 1
    ko = [
        "폭락", "금화교역", "태양인", "변동성", "레짐", "유동성", "붕괴", "회복",
        "리스크", "방어", "비트코인", "시장", "공포",
    ]
    terms: list[str] = []
    seen: set[str] = set()
    for t in ko + [w for w, _ in cnt.most_common(80)]:
        if t and t not in seen:
            seen.add(t)
            terms.append(t)

    terms_path = PILOT / "comp_atom02_codebook_terms_v1.json"
    codebook_path = PILOT / "genesis_gematria_4d_codebook_bench_seed_v1.json"
    terms_path.parent.mkdir(parents=True, exist_ok=True)
    terms_path.write_text(json.dumps(terms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_genesis_gematria_4d_codebook_v1.py"),
            "--terms-json",
            str(terms_path),
            "--out",
            str(codebook_path),
        ],
        check=True,
        cwd=str(ROOT),
    )

    texts = [str(c.get("raw_text", "")) for c in cases[:12] if c.get("raw_text")]
    inputs_path = PILOT / "comp_atom02_router_inputs_12_v1.json"
    inputs_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    router_out = PILOT / "comp_atom02_pointer_router_bench_seed_v1.json"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pointer_hash_snapping_router_v1.py"),
            "--codebook-json",
            str(codebook_path),
            "--inputs-json",
            str(inputs_path),
            "--enable-snap",
            "--out",
            str(router_out),
        ],
        check=True,
        cwd=str(ROOT),
    )

    doc = json.loads(router_out.read_text(encoding="utf-8"))
    sm = doc.get("summary") or {}
    summary = {
        "schema": "comp_atom02_bench_seed_run_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "term_count": len(terms),
        "case_count": len(texts),
        "codebook": str(codebook_path.relative_to(ROOT)).replace("\\", "/"),
        "router_summary": sm,
        "pointer_ok_rate": round(sm.get("pointer_candidate_ok_count", 0) / max(1, len(texts)), 4),
    }
    out_summary = PILOT / "comp_atom02_bench_seed_run_v1.json"
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
