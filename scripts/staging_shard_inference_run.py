#!/usr/bin/env python3
"""Build a staging log-domain shard JSON from inference_config_v1 + heuristics or optional Gemini.

Outputs under docs/final/artifacts/staging_shards/ by default so DomainSpecificRouter does not
auto-load it until copied to codebook/shards/ after review (Fact-Lock staging separation).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CONFIG = ROOT / "docs" / "final" / "artifacts" / "inference_config_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "staging_shards" / "zone_s_log_staging_v1.json"

# Heuristic expansion when --llm is off: common infra/log tokens (no PII), capped by config.
_HEURISTIC_LOG_TERMS: tuple[str, ...] = (
    "request_id",
    "span_id",
    "status",
    "method",
    "path",
    "latency_ms",
    "duration",
    "http",
    "grpc",
    "json",
    "logfmt",
    "syslog",
    "rfc3339",
    "iso8601",
    "debug",
    "info",
    "warn",
    "error",
    "fatal",
    "stack",
    "exception",
    "message",
    "pod",
    "container",
    "namespace",
    "node",
    "host",
    "service",
    "deployment",
    "replica",
    "region",
    "zone",
    "kafka",
    "redis",
    "postgres",
    "mysql",
    "query",
    "slow",
    "timeout",
    "retry",
    "circuit",
    "rate_limit",
    "quota",
    "auth",
    "oauth",
    "jwt",
    "tls",
    "health",
    "ready",
    "live",
    "startup",
    "shutdown",
    "oom",
    "gc",
    "cpu",
    "memory",
    "disk",
    "network",
    "egress",
    "ingress",
    "bandwidth",
    "packet",
    "loss",
    "rtt",
    "dns",
    "tcp",
    "connection",
    "pool",
    "queue",
    "backlog",
    "batch",
    "stream",
    "compress",
    "gzip",
    "protobuf",
    "offset",
    "partition",
    "consumer",
    "producer",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dedupe_lower(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        s = str(t).strip().lower()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _parse_llm_json_block(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _call_gemini_lexicon(
    *,
    cfg: dict[str, Any],
    sample_snippet: str,
    model: str,
    timeout_s: int,
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY required for --llm")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError("pip install google-genai required for --llm") from e

    llm = cfg.get("llm_expansion") or {}
    prompt_ver = str(llm.get("prompt_version", "v1"))
    anchors = cfg.get("anchors") or []
    aux = cfg.get("auxiliary_anchors") or []
    max_n = int(llm.get("max_lexicon_size") or 100)

    system = (
        "You propose technical log-pipeline vocabulary only. "
        "Output a single JSON object with keys: "
        "routing_keywords, must_keep_hard_terms, must_keep_soft_terms, guard_tokens — each an array of "
        "short ASCII/technical tokens (no secrets, no emails, no IPs, no user content). "
        f"Cap total new tokens across arrays at {max_n}. Prompt version: {prompt_ver}."
    )
    user = (
        f"Anchors (must appear in hard/soft as appropriate): {anchors!s}\n"
        f"Auxiliary: {aux!s}\n\n"
        "Optional sample lines (may be synthetic):\n"
        f"{sample_snippet[:12000]}\n"
    )

    # google.genai HttpOptions.timeout is milliseconds; API minimum deadline is 10s.
    timeout_ms = max(10_000, int(timeout_s) * 1000)
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_ms))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_text(text=user)],
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=float(llm.get("temperature") or 0.2),
        ),
    )
    return _parse_llm_json_block(resp.text or "")


def build_staging_shard(
    cfg: dict[str, Any],
    *,
    use_llm: bool,
    sample_path: Path | None,
    gemini_model: str,
    timeout_s: int,
) -> dict[str, Any]:
    shard_id = str(cfg.get("target_shard_id") or "zone_s_log_staging")
    domain = str(cfg.get("target_domain") or "log_staging")
    anchors = [str(x).strip().lower() for x in (cfg.get("anchors") or []) if str(x).strip()]
    aux = [str(x).strip().lower() for x in (cfg.get("auxiliary_anchors") or []) if str(x).strip()]
    max_n = int((cfg.get("llm_expansion") or {}).get("max_lexicon_size") or 100)

    sample_snippet = ""
    if sample_path and sample_path.is_file():
        sample_snippet = sample_path.read_text(encoding="utf-8", errors="replace")

    if use_llm:
        extra = _call_gemini_lexicon(
            cfg=cfg,
            sample_snippet=sample_snippet or "[no sample file; use anchors only]",
            model=gemini_model,
            timeout_s=timeout_s,
        )
        rk = _dedupe_lower(list(extra.get("routing_keywords") or []))
        mkh = _dedupe_lower(list(extra.get("must_keep_hard_terms") or []))
        mks = _dedupe_lower(list(extra.get("must_keep_soft_terms") or []))
        guard = _dedupe_lower(list(extra.get("guard_tokens") or []))
        if not rk and not mkh:
            raise RuntimeError("LLM returned empty routing_keywords/must_keep_hard_terms; retry or use heuristic")
    else:
        pool = list(anchors) + list(aux) + list(_HEURISTIC_LOG_TERMS)
        pool = _dedupe_lower(pool)[:max_n]
        rk = pool[: max_n // 2 + 8]
        mkh = _dedupe_lower(list(anchors) + list(aux))[:32]
        mks = [t for t in pool if t not in set(mkh)][: max_n // 3]
        guard = ["error", "fatal", "timeout", "oom", "tls", "auth", "health"]

    routing_keywords = _dedupe_lower(list(anchors) + list(aux) + rk)[:max_n]
    must_keep_hard = _dedupe_lower(list(anchors) + mkh)[:48]
    must_keep_soft = _dedupe_lower(mks)[:64]
    guard_tokens = _dedupe_lower(guard)[:24]

    return {
        "shard_id": shard_id,
        "domain": domain,
        "routing_keywords": routing_keywords,
        "must_keep_hard_terms": must_keep_hard,
        "must_keep_soft_terms": must_keep_soft,
        "guard_tokens": guard_tokens,
        "hangul_principle": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Inference spike: emit staging log shard JSON (artifacts path).")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="inference_config_v1.json")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Staging shard JSON output path")
    ap.add_argument(
        "--llm",
        action="store_true",
        help="Call Gemini for lexicon (needs GEMINI_API_KEY and google-genai)",
    )
    ap.add_argument(
        "--sample",
        type=Path,
        default=None,
        help="Optional log sample file (non-secret); overrides config sample_log_path if set",
    )
    ap.add_argument(
        "--gemini-model",
        default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        help="Model id when --llm (default GEMINI_MODEL or gemini-2.5-flash)",
    )
    ap.add_argument("--timeout", type=int, default=120, help="HTTP timeout seconds for --llm")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    if not cfg_path.is_file():
        print(f"FAIL: config not found: {cfg_path}", file=sys.stderr)
        return 1
    cfg = _load_json(cfg_path)

    sample = args.sample
    if sample is None:
        sp = str(cfg.get("sample_log_path") or "").strip()
        if sp:
            sample = (ROOT / sp.replace("/", os.sep)).resolve()

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        shard = build_staging_shard(
            cfg,
            use_llm=bool(args.llm),
            sample_path=sample,
            gemini_model=str(args.gemini_model),
            timeout_s=int(args.timeout),
        )
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    out_path.write_text(json.dumps(shard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(
        "Next (after review): copy to codebook/shards/ as zone_s_log_staging.json for local router tests; "
        "do not commit production routing without governance.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
