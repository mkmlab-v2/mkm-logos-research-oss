#!/usr/bin/env python3
"""Track B LLM distill with citation-lock gate — explicit opt-in only."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs/final/artifacts/logos_deep_research_distill_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_deep_research_distill_citation_lock_latest.json"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"
VERSE_CITE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*\.\d+\.\d+)\b")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def build_citation_lock(evidence_refs: list[dict[str, Any]]) -> dict[str, Any]:
    locked: list[dict[str, Any]] = []
    for ref in evidence_refs:
        if not isinstance(ref, dict):
            continue
        vid = ref.get("verse_id")
        qh = ref.get("quote_hash")
        if not isinstance(vid, str) or not vid:
            continue
        locked.append(
            {
                "verse_id": vid,
                "quote_hash": qh,
                "citation_required": True,
            }
        )
    return {
        "mode": "verse_id_quote_hash_only",
        "locked_count": len(locked),
        "locked_refs": locked,
        "policy": "LLM narrative may cite only locked verse_ids; orphan citations vetoed",
    }


def build_narrative_stub_ko(
    evidence_refs: list[dict[str, Any]],
    *,
    theme_title: str = "",
) -> dict[str, Any]:
    vids = [str(r.get("verse_id")) for r in evidence_refs if r.get("verse_id")][:8]
    title = theme_title or "Logos Track B"
    body = (
        f"[HYPO] {title} — 결정론적 서술 스텁. "
        f"앵커 구절 {len(vids)}건({', '.join(vids[:5])}{'…' if len(vids) > 5 else ''})만 인용 허용. "
        "교리·시장 단정 금지; 지휘관 검토 전 NON_GATING."
    )
    return {
        "labels": ["TRACK_B", "HYPO", "CITATION_LOCK_STUB"],
        "body_ko": body,
        "llm_invoked": False,
    }


def _ollama_generate(host: str, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    url = f"{host.rstrip('/')}/api/generate"
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        gen = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    text = str(gen.get("response") or "")
    return {
        "ok": bool(text.strip()),
        "response": text,
        "latency_ms": elapsed_ms,
    }


def _build_ollama_prompt(
    evidence_refs: list[dict[str, Any]],
    *,
    theme_title: str,
    max_snippets: int = 8,
) -> str:
    lines = [
        "[TRACK B / HYPO / NON_GATING] Korean research note only.",
        f"Theme: {theme_title or 'Logos Track B'}",
        "Rules: cite ONLY verse_ids listed below; prefix each claim with [HYPO]; "
        "no doctrine or market trading claims; 2-3 short paragraphs.",
        "",
        "Allowed verse_ids and surface text:",
    ]
    for ref in evidence_refs[:max_snippets]:
        vid = ref.get("verse_id")
        snip = str(ref.get("hash_tagged_snippet") or "")[:200]
        if vid:
            lines.append(f"- {vid}: {snip}")
    allowed = ", ".join(str(r.get("verse_id")) for r in evidence_refs[:max_snippets] if r.get("verse_id"))
    lines += ["", f"Allowed ids only: {allowed}"]
    return "\n".join(lines)


def _validate_citations(text: str, allowed: set[str]) -> dict[str, Any]:
    cited = set(VERSE_CITE_RE.findall(text or ""))
    orphan = sorted(cited - allowed)
    return {
        "cited_verse_ids": sorted(cited),
        "orphan_citations": orphan,
        "citation_valid": len(orphan) == 0,
    }


def try_ollama_distill_narrative(
    evidence_refs: list[dict[str, Any]],
    *,
    theme_title: str,
    host: str,
    model: str,
    timeout: int,
) -> dict[str, Any] | None:
    allowed = {str(r["verse_id"]) for r in evidence_refs if r.get("verse_id")}
    if not allowed:
        return None
    prompt = _build_ollama_prompt(evidence_refs, theme_title=theme_title)
    try:
        gen = _ollama_generate(host, model, prompt, timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {
            "labels": ["TRACK_B", "HYPO", "OLLAMA_FAIL"],
            "body_ko": "",
            "llm_invoked": True,
            "ollama_error": str(e)[:240],
            "citation_valid": False,
        }
    if not gen.get("ok"):
        return None
    text = str(gen["response"]).strip()
    validation = _validate_citations(text, allowed)
    return {
        "labels": ["TRACK_B", "HYPO", "CITATION_LOCK_OLLAMA"],
        "body_ko": text,
        "llm_invoked": True,
        "ollama_model": model,
        "latency_ms": gen.get("latency_ms"),
        **validation,
    }


def apply_citation_lock(
    distill: dict[str, Any],
    *,
    allow_llm_distill: bool,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    ollama_model: str = DEFAULT_OLLAMA_MODEL,
    ollama_timeout: int = 120,
) -> dict[str, Any]:
    evidence_refs = [r for r in (distill.get("evidence_refs") or []) if isinstance(r, dict)]
    if len(evidence_refs) < 1:
        raise ValueError("distill has no evidence_refs; citation-lock refused")

    out = dict(distill)
    lock = build_citation_lock(evidence_refs)
    out["citation_lock"] = lock

    theme_title = ""
    src = distill.get("source_slice") or {}
    if isinstance(src, dict):
        theme_title = str(src.get("theme_title_ko") or src.get("theme_id") or "")

    llm_enabled = allow_llm_distill and _truthy_env("MKM_LOGOS_LLM_DISTILL_ENABLE")
    narrative = build_narrative_stub_ko(evidence_refs, theme_title=theme_title)
    if llm_enabled:
        ollama_narr = try_ollama_distill_narrative(
            evidence_refs,
            theme_title=theme_title,
            host=ollama_host,
            model=ollama_model,
            timeout=ollama_timeout,
        )
        if ollama_narr and ollama_narr.get("body_ko") and ollama_narr.get("citation_valid"):
            narrative = ollama_narr
        elif ollama_narr:
            narrative["ollama_attempt"] = {
                k: ollama_narr.get(k)
                for k in ("ollama_error", "orphan_citations", "citation_valid", "latency_ms")
                if k in ollama_narr
            }
            narrative["body_ko"] += " [Ollama distill skipped: citation validation failed or empty]"
            narrative["llm_invoked"] = True
        else:
            narrative["body_ko"] += " [Ollama unreachable — stub retained]"
            narrative["llm_invoked"] = False
    else:
        narrative["llm_invoked"] = False
    out["distill_narrative_stub_ko"] = narrative

    out["provenance"] = dict(distill.get("provenance") or {})
    out["provenance"]["citation_lock_runner"] = "scripts/run_logos_llm_distill_citation_lock_v1.py"
    out["provenance"]["citation_lock_ts_utc"] = _utc_now()
    out["review_gate"] = {
        "status": "required",
        "reason_code": "citation_lock_applied",
        "notes": "지휘관 채택 전; locked_refs 외 인용 금지",
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--allow-llm-distill",
        action="store_true",
        help="Required flag before any LLM distill path (env MKM_LOGOS_LLM_DISTILL_ENABLE still required).",
    )
    ap.add_argument("--ollama-host", default=os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST))
    ap.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL))
    ap.add_argument("--ollama-timeout", type=int, default=120)
    args = ap.parse_args()

    if not args.allow_llm_distill:
        print(
            "Refusing: pass --allow-llm-distill to acknowledge B-track citation-lock distill.",
            file=sys.stderr,
        )
        return 2

    if not args.input.is_file():
        print(f"Missing input: {args.input}", file=sys.stderr)
        return 2

    distill = json.loads(args.input.read_text(encoding="utf-8-sig"))
    try:
        out_doc = apply_citation_lock(
            distill,
            allow_llm_distill=True,
            ollama_host=str(args.ollama_host).rstrip("/").replace("/v1", ""),
            ollama_model=str(args.ollama_model),
            ollama_timeout=max(10, int(args.ollama_timeout)),
        )
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_rel = (
        str(args.output.relative_to(ROOT)).replace("\\", "/")
        if args.output.is_relative_to(ROOT)
        else str(args.output)
    )
    print(
        json.dumps(
            {
                "ok": True,
                "out": out_rel,
                "locked_refs": out_doc["citation_lock"]["locked_count"],
                "llm_invoked": out_doc["distill_narrative_stub_ko"]["llm_invoked"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
