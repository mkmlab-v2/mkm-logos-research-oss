#!/usr/bin/env python3
"""Probe sentence-transformers readiness for Logos themed vector (B-track gate)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POLICY = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"
OUT_DEFAULT = ROOT / "reports/logos_sentence_transformers_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def probe(model_id: str) -> dict:
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    if os.environ.get("TRANSFORMERS_CACHE") and not os.environ.get("HF_HOME"):
        os.environ["HF_HOME"] = os.environ["TRANSFORMERS_CACHE"]
    try:
        from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

        model = load_sentence_transformer(model_id)
        dim = int(getattr(model, "get_sentence_embedding_dimension", lambda: 0)())
        return {
            "status": "ready",
            "model_id": model_id,
            "embedding_dim": dim,
            "error": None,
        }
    except Exception as e:
        return {
            "status": "blocked",
            "model_id": model_id,
            "embedding_dim": None,
            "error": f"{type(e).__name__}: {e}",
            "trace_tail": traceback.format_exc()[-800:],
        }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    if POLICY.is_file():
        try:
            pol = json.loads(POLICY.read_text(encoding="utf-8"))
            mid = (pol.get("embedding") or {}).get("model_id")
            if isinstance(mid, str) and mid.strip():
                model_id = mid.strip()
        except json.JSONDecodeError:
            pass

    result = probe(model_id)
    doc = {
        "schema": "logos_sentence_transformers_readiness_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "policy_path": "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json",
        "remediation_hint": "numpy<2 or isolated venv without tensorflow import chain; hash_stub remains default",
        **result,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "status": result["status"], "out": str(out_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
