#!/usr/bin/env python3
"""P2 LocalLock ask — fuzzy intent to identity key (metadata plane only).

Never reads secret_store or DPAPI. Optional local Ollama; deterministic fallback always available.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"
SCHEMA = "local_lock_ask_v1"
TOKEN_RE = re.compile(r"[\w가-힣]+", re.UNICODE)


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    try:
        from dotenv import load_dotenv

        if env_path.is_file():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass


def _ollama_host() -> str:
    return (os.getenv("OLLAMA_HOST") or DEFAULT_HOST).rstrip("/").replace("/v1", "")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL") or DEFAULT_MODEL


def _identity_store_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set (Windows-only default).")
    return Path(appdata) / "MKM" / "dev_identities_v1.json"


def load_catalog(path: Path | None) -> dict[str, dict[str, Any]]:
    env_override = os.environ.get("MKM_LOCAL_LOCK_IDENTITY_FILE")
    if path is None and env_override:
        path = Path(env_override)
    store_path = path or _identity_store_path()
    if not store_path.is_file():
        return {}
    raw = store_path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise ValueError("Identity catalog must be a JSON object.")
    return doc


def catalog_for_prompt(catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, meta in sorted(catalog.items()):
        if not isinstance(meta, dict):
            continue
        row: dict[str, Any] = {
            "key": key,
            "account_class": meta.get("account_class"),
            "email": meta.get("email"),
            "env_var_name": meta.get("env_var_name"),
            "login_url": meta.get("login_url"),
            "aliases": meta.get("aliases") or [],
        }
        rows.append(row)
    return rows


def _search_blob(key: str, meta: dict[str, Any]) -> str:
    parts = [
        key,
        str(meta.get("account_class") or ""),
        str(meta.get("email") or ""),
        str(meta.get("env_var_name") or ""),
        str(meta.get("login_url") or ""),
    ]
    login_url = meta.get("login_url")
    if login_url:
        try:
            host = urlparse(str(login_url)).netloc
            if host:
                parts.append(host)
        except Exception:  # noqa: BLE001
            pass
    parts.extend(str(x) for x in (meta.get("aliases") or []))
    return " ".join(parts).lower()


def score_deterministic(query: str, catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return []
    q_tokens = set(TOKEN_RE.findall(q))
    ranked: list[dict[str, Any]] = []
    for key, meta in catalog.items():
        if not isinstance(meta, dict):
            continue
        blob = _search_blob(key, meta)
        score = 0.0
        key_l = key.lower()
        if key_l in q or q in key_l:
            score += 0.45
        for alias in meta.get("aliases") or []:
            alias_l = str(alias).lower()
            if alias_l and (alias_l in q or q in alias_l):
                score += 0.35
        blob_tokens = set(TOKEN_RE.findall(blob))
        if q_tokens and blob_tokens:
            overlap = len(q_tokens & blob_tokens)
            score += (overlap / max(len(q_tokens), 1)) * 0.4
        email = str(meta.get("email") or "").lower()
        if email and (email in q or email.split("@")[0] in q_tokens):
            score += 0.15
        if score > 0:
            ranked.append({"key": key, "score": round(min(score, 1.0), 4)})
    ranked.sort(key=lambda row: (-row["score"], row["key"]))
    return ranked


def probe_ollama(host: str, timeout: int) -> dict[str, Any]:
    url = f"{host}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        names = [m.get("name") for m in tags.get("models") or [] if isinstance(m, dict)]
        return {"ok": True, "model_names": names[:10]}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": type(exc).__name__}


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        doc = json.loads(text)
        return doc if isinstance(doc, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]*\}", text, flags=re.DOTALL)
    if match:
        try:
            doc = json.loads(match.group(0))
            return doc if isinstance(doc, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def ollama_resolve_key(
    query: str,
    catalog_rows: list[dict[str, Any]],
    *,
    host: str,
    model: str,
    timeout: int,
) -> dict[str, Any]:
    allowed = {row["key"] for row in catalog_rows}
    prompt = (
        "Match the user query to exactly one identity registry key from the catalog below.\n"
        "Output JSON only: {\"resolved_key\": \"<key|null>\", \"confidence\": 0.0-1.0}\n"
        "Never output passwords, tokens, or secret values.\n"
        f"Catalog: {json.dumps(catalog_rows, ensure_ascii=False)}\n"
        f"User query: {query}\n"
        "JSON:"
    )
    body = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    url = f"{host}/api/generate"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        ms = round((time.perf_counter() - t0) * 1000.0, 4)
        parsed = _extract_json_object(str(doc.get("response") or ""))
        if not parsed:
            return {"ok": False, "latency_ms": ms, "error": "invalid_json"}
        resolved = parsed.get("resolved_key")
        if resolved in (None, "null", ""):
            return {"ok": True, "latency_ms": ms, "resolved_key": None, "confidence": float(parsed.get("confidence") or 0)}
        if resolved not in allowed:
            return {"ok": False, "latency_ms": ms, "error": "key_not_in_catalog"}
        confidence = float(parsed.get("confidence") or 0.5)
        return {
            "ok": True,
            "latency_ms": ms,
            "resolved_key": str(resolved),
            "confidence": max(0.0, min(confidence, 1.0)),
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "ok": False,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            "error": type(exc).__name__,
        }


def resolve_query(
    query: str,
    catalog: dict[str, dict[str, Any]],
    *,
    skip_ollama: bool,
    min_confidence: float,
    ollama_timeout: int,
) -> dict[str, Any]:
    candidates = score_deterministic(query, catalog)
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "query_excerpt": query[:120],
        "research_only": True,
        "send_gate": "HOLD",
        "secret_plane": "not_accessed",
        "candidates": candidates[:5],
        "resolved_key": None,
        "confidence": 0.0,
        "resolver": "none",
    }
    if not catalog:
        result["error"] = "empty_catalog"
        return result

    best = candidates[0] if candidates else None
    ollama_doc: dict[str, Any] | None = None
    if not skip_ollama:
        host = _ollama_host()
        model = _ollama_model()
        probe = probe_ollama(host, min(ollama_timeout, 10))
        if probe.get("ok"):
            rows = catalog_for_prompt(catalog)
            ollama_doc = ollama_resolve_key(
                query, rows, host=host, model=model, timeout=ollama_timeout
            )
            if ollama_doc.get("ok") and ollama_doc.get("resolved_key"):
                result["resolved_key"] = ollama_doc["resolved_key"]
                result["confidence"] = float(ollama_doc.get("confidence") or 0)
                result["resolver"] = "ollama_neuro"
                result["ollama"] = {
                    "host": host,
                    "model": model,
                    "latency_ms": ollama_doc.get("latency_ms"),
                }
                return result
        result["ollama"] = {"skipped": False, "probe": probe, "attempt": ollama_doc}

    if best and best["score"] >= min_confidence:
        result["resolved_key"] = best["key"]
        result["confidence"] = best["score"]
        result["resolver"] = "symbolic_fallback"
    return result


def main() -> int:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="LocalLock P2 ask (identity metadata only).")
    parser.add_argument("--query", required=True, help="Natural-language intent (key lookup only).")
    parser.add_argument("--catalog-file", type=Path, help="Override identity catalog JSON path.")
    parser.add_argument("--skip-ollama", action="store_true", help="Deterministic fallback only.")
    parser.add_argument("--min-confidence", type=float, default=0.25)
    parser.add_argument("--ollama-timeout", type=int, default=30)
    args = parser.parse_args()

    try:
        catalog = load_catalog(args.catalog_file)
        doc = resolve_query(
            args.query,
            catalog,
            skip_ollama=args.skip_ollama,
            min_confidence=args.min_confidence,
            ollama_timeout=args.ollama_timeout,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": SCHEMA, "ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("resolved_key") else 1


if __name__ == "__main__":
    sys.exit(main())
