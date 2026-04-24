# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.7, L:0.8, K:0.7, M:0.4}
# Balance: 86
# Purpose: Provide pluggable text-to-4D projection interfaces.
# Keywords: projection, interface, embedding, deterministic, quaternion
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Projection interfaces for dimensional projection bridge."""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from math import sqrt
from pathlib import Path
from typing import Protocol

from routers.dimensional_projection.runtime_lock import enforce_runtime_lock


def _normalize_signed(value: float) -> float:
    return round(max(-1.0, min(1.0, value)), 6)


class TextEmbedder(Protocol):
    """Pluggable embedder contract."""

    def embed(self, text: str) -> list[float]:
        """Return a deterministic embedding vector for input text."""


class ProjectionEngine(ABC):
    """Abstract projector contract for future embedding-based engines."""

    @abstractmethod
    def project(self, text: str) -> dict[str, float]:
        """Project input text into 4D (S, L, K, M)."""


class HashProjectionEngine(ProjectionEngine):
    """Current MVP projector with deterministic lexical/hash features."""

    def project(self, text: str) -> dict[str, float]:
        text_len = max(1, len(text))
        alpha = sum(ch.isalpha() for ch in text) / text_len
        digit = sum(ch.isdigit() for ch in text) / text_len
        upper = sum(ch.isupper() for ch in text) / text_len
        whitespace = sum(ch.isspace() for ch in text) / text_len

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        h = [int.from_bytes(digest[i : i + 4], "big") / 0xFFFFFFFF for i in (0, 4, 8, 12)]

        return {
            "S": _normalize_signed((alpha * 1.3) - 0.5 + (h[0] - 0.5) * 0.4),
            "L": _normalize_signed((1.0 - digit) - 0.5 + (h[1] - 0.5) * 0.4),
            "K": _normalize_signed((1.0 - whitespace) - 0.5 + (h[2] - 0.5) * 0.4),
            "M": _normalize_signed((upper * 1.8) - 0.2 + (h[3] - 0.5) * 0.4),
        }


class EmbeddingProjectionEngine(ProjectionEngine):
    """
    Future-ready embedding projector.

    For now this wraps an embedder contract and maps the first 4 dims. It enables
    model swap without touching router logic.
    """

    def __init__(self, embedder: TextEmbedder):
        self._embedder = embedder
        self._fallback = HashProjectionEngine()

    def project(self, text: str) -> dict[str, float]:
        try:
            vec = self._embedder.embed(text)
        except Exception:
            return self._fallback.project(text)
        if len(vec) < 4:
            vec = vec + [0.0] * (4 - len(vec))
        # Use aggregated signals instead of only the first dimensions.
        n = len(vec)
        abs_mean = sum(abs(v) for v in vec) / n
        sq_mean = sqrt(sum(v * v for v in vec) / n)
        pos_ratio = sum(1 for v in vec if v > 0) / n
        head_mean = sum(vec[: min(32, n)]) / min(32, n)
        tail = vec[-min(32, n) :]
        tail_mean = sum(tail) / len(tail)

        return {
            "S": _normalize_signed((head_mean * 1.2) + (pos_ratio - 0.5) * 0.6),
            "L": _normalize_signed((tail_mean * 1.1) + (sq_mean - 0.25) * 0.5),
            "K": _normalize_signed((vec[0] + vec[1] + vec[2] + vec[3]) / 4.0),
            "M": _normalize_signed((abs_mean - 0.25) * 1.4),
        }


class SentenceTransformersEmbedder:
    """SentenceTransformers embedder with lazy model loading."""

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load()
        vector = model.encode(text)
        if hasattr(vector, "tolist"):
            return vector.tolist()
        return [float(v) for v in vector]


def get_projection_engine() -> ProjectionEngine:
    """
    Resolve active projector implementation.

    `DIMENSIONAL_PROJECTION_ENGINE=hash|embedding`
    """
    engine = os.getenv("DIMENSIONAL_PROJECTION_ENGINE", "hash").strip().lower()
    if engine == "embedding":
        model_name = os.getenv("DIMENSIONAL_PROJECTION_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
        try:
            embedder = SentenceTransformersEmbedder(model_name)
            return EmbeddingProjectionEngine(embedder)
        except Exception:
            # Hard fail would break API startup. Keep fail-safe fallback.
            return HashProjectionEngine()
    return HashProjectionEngine()


_ENGINE_CACHE: dict[str, ProjectionEngine] = {}


def _resolve_eval_report_path() -> Path:
    env = os.getenv("DIMENSIONAL_PROJECTION_ENGINE_EVAL_REPORT", "").strip()
    if env:
        return Path(env)
    return Path("C:/workspace/reports/dimensional_projection_bridge/engine_eval_multi_policy_latest.json")


def _resolve_engine_override_path() -> Path:
    env = os.getenv("DIMENSIONAL_PROJECTION_ENGINE_OVERRIDE_FILE", "").strip()
    if env:
        return Path(env)
    freeze_path = Path("C:/workspace/reports/dimensional_projection_bridge/freeze/engine_overrides_latest.json")
    if freeze_path.is_file():
        return freeze_path
    return Path("C:/workspace/reports/dimensional_projection_bridge/engine_overrides_latest.json")


def _engine_from_name(name: str) -> ProjectionEngine:
    key = name.strip().lower()
    if key in _ENGINE_CACHE:
        return _ENGINE_CACHE[key]
    if key == "embedding":
        model_name = os.getenv("DIMENSIONAL_PROJECTION_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
        try:
            engine = EmbeddingProjectionEngine(SentenceTransformersEmbedder(model_name))
        except Exception:
            engine = HashProjectionEngine()
    else:
        engine = HashProjectionEngine()
    _ENGINE_CACHE[key] = engine
    return engine


def _pick_engine_name_from_override(policy_id: str) -> str | None:
    path = _resolve_engine_override_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    overrides = payload.get("policy_engine_overrides", {}) if isinstance(payload, dict) else {}
    if not isinstance(overrides, dict):
        return None
    item = overrides.get(policy_id)
    if not isinstance(item, dict):
        return None
    engine_name = str(item.get("engine", "")).strip().lower()
    if engine_name in {"hash", "embedding"}:
        return engine_name
    return None


def _read_override_item(policy_id: str) -> dict | None:
    path = _resolve_engine_override_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    overrides = payload.get("policy_engine_overrides", {}) if isinstance(payload, dict) else {}
    if not isinstance(overrides, dict):
        return None
    item = overrides.get(policy_id)
    if not isinstance(item, dict):
        return None
    return item


def _pick_engine_name_from_report(policy_id: str) -> str | None:
    path = _resolve_eval_report_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    ranked = (((payload or {}).get("policy_comparison") or {}).get("ranked") or [])
    if isinstance(ranked, list):
        for row in ranked:
            if not isinstance(row, dict):
                continue
            if str(row.get("policy_id", "")).strip() != policy_id:
                continue
            engine_name = str(row.get("engine", "")).strip().lower()
            if engine_name == "embedding_local_baseline":
                return "embedding"
            if engine_name in {"hash", "embedding"}:
                return engine_name
    return None


def _read_ranked_item(policy_id: str) -> dict | None:
    path = _resolve_eval_report_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    ranked = (((payload or {}).get("policy_comparison") or {}).get("ranked") or [])
    if isinstance(ranked, list):
        for row in ranked:
            if not isinstance(row, dict):
                continue
            if str(row.get("policy_id", "")).strip() == policy_id:
                return row
    return None


def get_projection_engine_for_policy(policy_id: str) -> ProjectionEngine:
    """
    Resolve projection engine automatically.

    Priority:
    1) `DIMENSIONAL_PROJECTION_ENGINE` explicit override
    2) Policy engine override file (safety fallback gate)
    3) Best engine from multi-policy evaluation report
    4) Safe fallback to hash
    """
    enforce_runtime_lock()
    explicit = os.getenv("DIMENSIONAL_PROJECTION_ENGINE", "").strip().lower()
    if explicit in {"hash", "embedding"}:
        return _engine_from_name(explicit)

    override = _pick_engine_name_from_override(policy_id)
    if override in {"hash", "embedding"}:
        return _engine_from_name(override)

    recommended = _pick_engine_name_from_report(policy_id)
    if recommended in {"hash", "embedding"}:
        return _engine_from_name(recommended)
    return _engine_from_name("hash")


def get_projection_resolution_for_policy(policy_id: str) -> dict:
    """
    Return engine selection details for observability and audits.
    """
    enforce_runtime_lock()
    explicit = os.getenv("DIMENSIONAL_PROJECTION_ENGINE", "").strip().lower()
    if explicit in {"hash", "embedding"}:
        return {
            "policy_id": policy_id,
            "selected_engine": explicit,
            "selection_source": "env",
            "unsafe_allow_rate": None,
            "override_reason": None,
        }

    override_item = _read_override_item(policy_id)
    if isinstance(override_item, dict):
        engine = str(override_item.get("engine", "")).strip().lower()
        if engine in {"hash", "embedding"}:
            return {
                "policy_id": policy_id,
                "selected_engine": engine,
                "selection_source": "override",
                "unsafe_allow_rate": override_item.get("unsafe_allow_rate"),
                "override_reason": override_item.get("reason"),
            }

    ranked_item = _read_ranked_item(policy_id)
    if isinstance(ranked_item, dict):
        engine_name = str(ranked_item.get("engine", "")).strip().lower()
        mapped = "embedding" if engine_name == "embedding_local_baseline" else engine_name
        if mapped in {"hash", "embedding"}:
            return {
                "policy_id": policy_id,
                "selected_engine": mapped,
                "selection_source": "report",
                "unsafe_allow_rate": ranked_item.get("unsafe_allow_rate"),
                "override_reason": None,
            }

    return {
        "policy_id": policy_id,
        "selected_engine": "hash",
        "selection_source": "fallback",
        "unsafe_allow_rate": None,
        "override_reason": "no_policy_match",
    }

