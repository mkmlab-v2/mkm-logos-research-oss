"""ANN lite embedding backends for Track B (policy-gated neural path)."""
from __future__ import annotations

import hashlib
import os
import time
import warnings
from typing import Any

EMBEDDING_HASH_STUB = "hash_stub_v1"
EMBEDDING_SENTENCE_TRANSFORMERS = "sentence_transformers_v1"


def neural_embedding_allowed(policy_doc: dict[str, Any], allow_bypass: bool) -> tuple[bool, str]:
    if allow_bypass:
        return True, "allow_stub_policy_embedding"
    if policy_doc.get("status") == "active":
        return True, "policy_active"
    return (
        False,
        "Neural embeddings require policy.status=active or --allow-stub-policy-embedding (dev only).",
    )


def verse_text_for_embedding(row: dict[str, Any], max_chars: int) -> str:
    raw = row.get("verse_text") or row.get("text")
    if raw is None:
        span = row.get("text_span")
        if isinstance(span, dict):
            raw = span.get("original_script_text") or span.get("text")
    if raw is None:
        raw = row.get("verse_id")
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) > max_chars:
        return s[:max_chars]
    return s


def load_sentence_transformer(model_id: str) -> Any:
    # Keep Hugging Face stack on torch-only path to avoid optional TF/protobuf noise.
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    # If legacy TRANSFORMERS_CACHE is pre-set, mirror it to HF_HOME to avoid deprecation warning.
    if os.environ.get("TRANSFORMERS_CACHE") and not os.environ.get("HF_HOME"):
        os.environ["HF_HOME"] = os.environ["TRANSFORMERS_CACHE"]
    warnings.filterwarnings(
        "ignore",
        message="Using `TRANSFORMERS_CACHE` is deprecated and will be removed in v5 of Transformers. Use `HF_HOME` instead.",
        category=FutureWarning,
    )
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise RuntimeError(
            "sentence-transformers is not installed. pip install sentence-transformers"
        ) from e
    return SentenceTransformer(model_id)


def encode_sentence_transformer_batch(
    model: Any,
    rows: list[dict[str, Any]],
    *,
    max_chars: int,
    normalize: bool,
    start_monotonic: float,
    max_wall_seconds: float,
) -> list[tuple[str, bytes, int]]:
    import numpy as np

    if time.monotonic() - start_monotonic > max_wall_seconds:
        raise TimeoutError("max_wall_seconds exceeded before encode")
    texts = [verse_text_for_embedding(r, max_chars) or str(r["verse_id"]) for r in rows]
    emb = model.encode(
        texts,
        batch_size=min(64, len(texts)),
        normalize_embeddings=normalize,
        show_progress_bar=False,
    )
    out: list[tuple[str, bytes, int]] = []
    for i, row in enumerate(rows):
        vid = str(row["verse_id"])
        flat = np.asarray(emb[i], dtype=np.float32)
        blob = flat.tobytes()
        out.append((vid, blob, int(flat.shape[0])))
    return out


def sha256_blob(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()
