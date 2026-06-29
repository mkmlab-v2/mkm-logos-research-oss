#!/usr/bin/env python3
"""
NVIDIA NIM (70B) + optional local Ollama embed — Logos/B-track research handoff.

Reads DE anchor probe JSON and/or Logos insight MD; produces [HYPO] synthesis.
Does NOT wire into NG-40 codec, Track A, or general_prophecy L1.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DEFAULT_PROBE = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
DEFAULT_LOGOS_MD = ROOT / "reports/logos_2026_ai_industry_max_util_insight_v1_latest.md"
DEFAULT_OUT_JSON = ROOT / "reports/nim_logos_research_handoff_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/nim_logos_research_handoff_v1_latest.md"
REGISTRY = ROOT / "docs/final/artifacts/nvidia_nim_model_registry_v1.json"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass


def _api_key() -> str | None:
    return os.getenv("NVIDIA_API_KEY") or os.getenv("NGC_API_KEY")


def _embed_local(text: str, timeout: int = 60) -> int | None:
    host = (os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/").replace("/v1", "")
    body = json.dumps({"model": "nomic-embed-text:latest", "prompt": text[:8000]}).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        vec = data.get("embedding") or []
        return len(vec)
    except Exception:
        return None


def _read_probe(path: Path, max_hits: int) -> str:
    if not path.is_file():
        return ""
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    lines = [f"probe_schema={doc.get('schema')} ok={doc.get('ok')}"]
    for hit in (doc.get("hits") or [])[:max_hits]:
        if not isinstance(hit, dict):
            continue
        lines.append(
            f"- {hit.get('probe_id')}: {hit.get('title', '')[:80]} | snippet={str(hit.get('snippet', ''))[:200]}"
        )
    return "\n".join(lines)


def _read_md(path: Path, max_chars: int) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def main() -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-json", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--logos-md", type=Path, default=DEFAULT_LOGOS_MD)
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--skip-embed", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    probe_ctx = _read_probe(args.probe_json, 8)
    logos_ctx = _read_md(args.logos_md, 6000)
    embed_dim = None if args.skip_embed else _embed_local(probe_ctx + logos_ctx[:2000])

    prompt = f"""You are an MKM B-track research assistant. Output ONLY in Korean.

Rules:
- Tag [HYPO] and [NON_GATING] on 성경(Logos) lines.
- Use this exact block order at the top:
  Field → Lens(사상/명리/성경) → Conflict → Final Action → Fact-Lock paths → 격벽 한 줄
- Final Action must be WATCH or HOLD (no trading GO).
- Do NOT claim Track A promotion or live trading.
- NVIDIA NIM cloud inference only; not clinical or price prophecy.

Context A — Discovery Engine anchor probe (excerpt):
{probe_ctx or '(no probe file)'}

Context B — Logos AI industry insight (excerpt):
{logos_ctx or '(no logos md)'}

Local embed dim (if any): {embed_dim}

Task: 5-8 bullets synthesizing how DE anchors relate to Logos GraphRAG themes (hubris, trade hub, governance).
End with "끝."
"""

    key = _api_key()
    if not key:
        print("missing NVIDIA_API_KEY", file=sys.stderr)
        return 2
    sys.path.insert(0, str(ROOT))
    from scripts.nvidia_nim_common_v1 import chat_with_fallback

    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    chat, attempts = chat_with_fallback(key, registry, prompt, args.max_tokens)
    nim_model = chat.get("model") or (attempts[-1]["model"] if attempts else "")
    finished = datetime.now(timezone.utc).isoformat()
    doc = {
        "schema": "nim_logos_research_handoff_v1",
        "finished_at_utc": finished,
        "lane": "b_track_research_only",
        "research_only": True,
        "gating": "NON_GATING",
        "nim_model": nim_model,
        "model_attempts": attempts,
        "inputs": {
            "probe_json": str(args.probe_json),
            "logos_md": str(args.logos_md),
            "local_embed_dim": embed_dim,
        },
        "chat": chat,
        "forbidden": ["track_a_promotion", "live_trading", "ng40_codec_auto_wire", "gp_l1_merge"],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_body = chat.get("text") or json.dumps(chat, ensure_ascii=False, indent=2)
    md = (
        f"# NIM Logos research handoff v1\n\n"
        f"**generated:** {finished} · **model:** {nim_model} · `[HYPO]` `[NON_GATING]`\n\n"
        f"{md_body}\n"
    )
    args.out_md.write_text(md, encoding="utf-8")

    if chat.get("ok"):
        print(chat["text"])
        print(f"\n[ok] {args.out_json}\n[ok] {args.out_md}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
