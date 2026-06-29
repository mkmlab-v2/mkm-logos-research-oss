#!/usr/bin/env python3
"""Logos Studio ST embedding sidecar — keep model warm (localhost HTTP).

Reproduce:
  py scripts/logos_studio_embedding_sidecar_v1.py --port 18765
  curl -s http://127.0.0.1:18765/health
  curl -s -X POST http://127.0.0.1:18765/encode -H 'Content-Type: application/json' -d '{"query":"네피림"}'
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PORT = 18765
DEFAULT_INDEX = ROOT / "docs/final/artifacts/logos_studio_semantic_router_embedding_index_v1_latest.json"
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_MODEL: Any = None
_MODEL_ID: str | None = None
_STARTED_AT: float | None = None
_ENCODE_COUNT = 0


def _resolve_model_id(index_json: Path, override: str) -> str:
    if override.strip():
        return override.strip()
    if index_json.is_file():
        idx = json.loads(index_json.read_text(encoding="utf-8-sig"))
        return str(idx.get("model_id") or DEFAULT_MODEL)
    return DEFAULT_MODEL


def _load_model(model_id: str) -> Any:
    global _MODEL, _MODEL_ID, _STARTED_AT
    if _MODEL is not None:
        return _MODEL
    from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

    t0 = time.perf_counter()
    _MODEL = load_sentence_transformer(model_id)
    _MODEL_ID = model_id
    _STARTED_AT = time.perf_counter() - t0
    return _MODEL


def _encode_query(query: str, model_id: str) -> dict[str, Any]:
    global _ENCODE_COUNT
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}
    model = _load_model(model_id)
    t0 = time.perf_counter()
    vec = model.encode([q], normalize_embeddings=True, show_progress_bar=False)[0]
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    _ENCODE_COUNT += 1
    return {
        "ok": True,
        "model_id": model_id,
        "vector_dim": int(vec.shape[0]),
        "vector": vec.tolist(),
        "encode_ms": elapsed_ms,
        "warm": _MODEL is not None,
    }


class _Handler(BaseHTTPRequestHandler):
    model_id: str = DEFAULT_MODEL

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        return

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        self._send_json(
            200,
            {
                "ok": True,
                "model_loaded": _MODEL is not None,
                "model_id": _MODEL_ID or self.model_id,
                "load_seconds": round(_STARTED_AT or 0.0, 3),
                "encode_count": _ENCODE_COUNT,
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/encode":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "invalid_json"})
            return
        query = str(body.get("query") or "")
        try:
            out = _encode_query(query, self.model_id)
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"ok": False, "error": str(exc)[:240]})
            return
        code = 200 if out.get("ok") else 400
        self._send_json(code, out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--model-id", default="")
    ap.add_argument("--index-json", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--preload", action="store_true", help="Load ST model before accepting requests")
    args = ap.parse_args()

    model_id = _resolve_model_id(args.index_json, args.model_id)
    if args.preload:
        print(f"[sidecar] preloading model: {model_id}", flush=True)
        _load_model(model_id)
        print(f"[sidecar] model ready in {_STARTED_AT:.1f}s", flush=True)

    _Handler.model_id = model_id
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"[sidecar] listening http://{args.host}:{args.port} model={model_id}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[sidecar] shutdown", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
