# -*- coding: utf-8 -*-
"""
Rehearsal: compress `content` with same experimental compressor as pilot, recompute vector_4d via hybrid_vectorize.

- **Never writes under memory/** unless --out-dir is explicitly set to a path under memory (default: reports/memory/rehearsal_revector_out).
- Default --dry-run: prints metrics + optional JSON sidecar only.

Exit 0 on success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from scripts.report_multilens_performance_eval import (  # noqa: E402
    _compress_experimental,
    _ensure_sensitive_tokens_preserved,
    _jaccard,
    _reconstruct_experimental_from_raw,
)
from tools.core.hybrid_vectorizer import hybrid_vectorize  # noqa: E402

MUST_KEEP = {"사상의학", "체질", "sasang", "myeongni", "myeongri", "bible"}


def _norm_v4(raw: Any) -> Dict[str, float]:
    if not isinstance(raw, dict):
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    out: Dict[str, float] = {}
    for k in ("S", "L", "K", "M"):
        try:
            out[k] = float(raw.get(k, 0.25))
        except (TypeError, ValueError):
            out[k] = 0.25
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True, help=".mkm-memory file path.")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "reports" / "memory" / "rehearsal_revector_out",
        help="Output directory (not memory/ by default).",
    )
    ap.add_argument("--strategy", choices=("A", "B", "C"), default="B")
    ap.add_argument("--intensity", choices=("high", "ultra", "extreme"), default="ultra")
    ap.add_argument("--hangul", choices=("on", "off"), default="on")
    ap.add_argument("--dry-run", action="store_true", help="Do not write output .mkm-memory copy.")
    args = ap.parse_args()

    inp = args.input
    if not inp.is_file():
        print(f"ERROR: missing {inp}", file=sys.stderr)
        return 2

    doc = json.loads(inp.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        print("ERROR: not a JSON object", file=sys.stderr)
        return 2
    content = doc.get("content")
    if not isinstance(content, str):
        content = ""
    use_hangul = args.hangul == "on"
    cand = _compress_experimental(
        content,
        strategy=args.strategy,
        intensity=args.intensity,
        must_keep=set(MUST_KEEP),
        use_hangul_principle=use_hangul,
    )
    cand = _ensure_sensitive_tokens_preserved(content, cand, set(MUST_KEEP))
    rec = _reconstruct_experimental_from_raw(
        raw=content,
        compressed_candidate=cand,
        use_hangul_principle=use_hangul,
    )
    j = _jaccard(content, rec)
    raw_len = len(content)
    saving = 1.0 - (len(cand) / raw_len) if raw_len else 0.0

    hv = hybrid_vectorize(text=rec)
    v4_new = _norm_v4(hv.get("vector_4d"))
    v4_old = _norm_v4(doc.get("vector_4d"))

    report = {
        "schema": "rehearsal_recompress_revector_v1",
        "input": str(inp.resolve()),
        "profile": {
            "strategy": args.strategy,
            "intensity": args.intensity,
            "use_hangul_principle": use_hangul,
        },
        "metrics": {
            "raw_chars": raw_len,
            "compressed_chars": len(cand),
            "char_saving_rate": round(saving, 6),
            "jaccard_raw_vs_reconstruct": round(j, 6),
        },
        "vector_4d_before": v4_old,
        "vector_4d_after_hybrid_on_reconstructed_text": v4_new,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    side = args.out_dir / f"{inp.stem}_rehearsal_report.json"
    side.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(side.resolve()), "dry_run": bool(args.dry_run)}, indent=2))

    if args.dry_run:
        return 0

    out_doc = dict(doc)
    out_doc["content"] = rec
    out_doc["vector_4d"] = v4_new
    meta = out_doc.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    meta["rehearsal_revector"] = {
        "profile": report["profile"],
        "source_input": str(inp.resolve()),
    }
    out_doc["metadata"] = meta
    out_path = args.out_dir / inp.name
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"wrote_mkm_memory": str(out_path.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
