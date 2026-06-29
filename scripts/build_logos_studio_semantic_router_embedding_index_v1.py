#!/usr/bin/env python3
"""Build preset embedding index for Logos Studio semantic router tier-1 (ST).

Reproduce:
  py scripts/build_logos_studio_semantic_router_embedding_index_v1.py
  py scripts/build_logos_studio_semantic_router_embedding_index_v1.py --backend hash_stub_v1
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_vector_hash_stub_v1 import hash_stub_v1_embedding_floats  # noqa: E402

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM_STUB = 64


def _preset_seed(preset: dict[str, Any]) -> str:
    parts = [str(preset.get("prompt_ko") or "")]
    parts.extend(str(k) for k in (preset.get("keywords") or [])[:12])
    return " | ".join(p for p in parts if p.strip())


def _encode_st(model_id: str, texts: list[str]) -> list[list[float]]:
    from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

    model = load_sentence_transformer(model_id)
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [row.tolist() for row in emb]


def build_index(
    presets_doc: dict[str, Any],
    *,
    backend: str,
    model_id: str,
    dim_stub: int,
) -> dict[str, Any]:
    presets = presets_doc.get("presets") or []
    seeds = [_preset_seed(p) for p in presets]
    vectors: list[dict[str, Any]] = []
    if backend == "sentence_transformers":
        encoded = _encode_st(model_id, seeds)
        dim = len(encoded[0]) if encoded else 0
        for preset, vec in zip(presets, encoded):
            vectors.append(
                {
                    "preset_id": str(preset.get("id")),
                    "seed_preview": seeds[len(vectors)][:120],
                    "vector": vec,
                }
            )
    else:
        dim = dim_stub
        for preset, seed in zip(presets, seeds):
            vectors.append(
                {
                    "preset_id": str(preset.get("id")),
                    "seed_preview": seed[:120],
                    "vector": hash_stub_v1_embedding_floats(seed, dim_stub),
                }
            )
    return {
        "schema": "logos_studio_semantic_router_embedding_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "backend": backend,
        "model_id": model_id if backend == "sentence_transformers" else None,
        "vector_dim": dim,
        "preset_count": len(vectors),
        "min_cosine_threshold": 0.42,
        "vectors": vectors,
        "honesty": {
            "hash_stub_non_semantic": backend == "hash_stub_v1",
            "runtime_ts_uses_lexical_tier_first": True,
        },
        "reproduce": "py scripts/build_logos_studio_semantic_router_embedding_index_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--backend",
        choices=("sentence_transformers", "hash_stub_v1"),
        default="sentence_transformers",
    )
    ap.add_argument("--model-id", default=DEFAULT_MODEL)
    ap.add_argument("--dim-stub", type=int, default=DIM_STUB)
    args = ap.parse_args()
    doc = json.loads(args.presets.read_text(encoding="utf-8-sig"))
    index = build_index(doc, backend=args.backend, model_id=args.model_id, dim_stub=args.dim_stub)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "backend": args.backend, "preset_count": index["preset_count"], "out": str(args.out)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
