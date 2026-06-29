#!/usr/bin/env python3
"""[HYPO] NVIDIA NIM synthesis on DE probe hits — staging for commander LUT review."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ENV_PATH = ROOT / ".env"
REGISTRY = ROOT / "docs/final/artifacts/nvidia_nim_model_registry_v1.json"
PROBE_DEFAULT = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/ng40_de_probe_nim_synthesis_v1_latest.json"

VERSE_REF_RE = re.compile(r"verse:([A-Za-z0-9_.:]+)", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hits_context(hits: list[dict[str, Any]], max_snippet_chars: int) -> str:
    parts: list[str] = []
    for i, h in enumerate(hits[:8], 1):
        title = str(h.get("title") or "")
        snips = h.get("snippets") or []
        snip = " ".join(str(s) for s in snips if s)[:max_snippet_chars]
        parts.append(f"[{i}] {title}\n{snip}")
    return "\n\n".join(parts)


def _extract_verse_refs(text: str) -> list[str]:
    return list(dict.fromkeys(VERSE_REF_RE.findall(text)))[:16]


def _synthesize_probe(
    probe: dict[str, Any],
    *,
    key: str,
    registry: dict,
    max_snippet_chars: int,
    max_tokens: int,
    dry_run: bool,
) -> dict[str, Any]:
    ctx = _hits_context(probe.get("hits") or [], max_snippet_chars)
    user = (
        f"Probe: {probe.get('probe_id')} ({probe.get('label_ko')})\n"
        f"Role: {probe.get('role')}\n"
        f"DE query: {probe.get('query')}\n\n"
        f"Discovery Engine snippets:\n{ctx}\n\n"
        "Respond in JSON only with keys: "
        "anchor_candidates (array of {label, rationale, confidence: low|medium}), "
        "verse_refs_guess (array of strings), "
        "human_review_note (one sentence Korean), "
        "non_gating_disclaimer (must mention NON_GATING). "
        "Never claim price prophecy or trading GO."
    )
    row: dict[str, Any] = {
        "probe_id": probe.get("probe_id"),
        "label_ko": probe.get("label_ko"),
        "hit_count": probe.get("hit_count"),
        "dry_run": dry_run,
    }
    if dry_run:
        row["status"] = "dry_run_skipped"
        row["verse_refs_from_snippets"] = _extract_verse_refs(ctx)
        return row

    from scripts.nvidia_nim_common_v1 import chat_with_fallback

    prompt = (
        "[HYPO] MKM B-track staging only. No Track A, no live trading.\n\n" + user
    )
    chat, attempts = chat_with_fallback(key, registry, prompt, max_tokens)
    row["nim_ok"] = chat.get("ok")
    row["model_attempts"] = attempts
    row["model"] = chat.get("model")
    if not chat.get("ok"):
        row["error"] = chat.get("error")
        row["status"] = "nim_error"
        return row
    text = chat.get("text") or ""
    row["raw_reply"] = text[:4000]
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned)
        row["synthesis"] = parsed
        row["status"] = "ok"
    except json.JSONDecodeError:
        row["synthesis"] = {"human_review_note": text[:500]}
        row["status"] = "ok_non_json"
    row["verse_refs_from_snippets"] = _extract_verse_refs(ctx)
    if row.get("synthesis"):
        vg = row["synthesis"].get("verse_refs_guess") or []
        row["verse_refs_merged"] = list(
            dict.fromkeys(list(vg) + row["verse_refs_from_snippets"])
        )[:16]
    return row


def main() -> int:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass

    from scripts.nvidia_nim_common_v1 import api_key

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe-json", type=Path, default=PROBE_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--max-probes", type=int, default=0)
    ap.add_argument("--max-snippet-chars", type=int, default=600)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.probe_json.is_file():
        print(json.dumps({"error": "missing_probe"}))
        return 2

    key = api_key()
    if not args.dry_run and not key:
        print(json.dumps({"error": "missing_NVIDIA_API_KEY"}))
        return 2

    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    probe_doc = json.loads(args.probe_json.read_text(encoding="utf-8-sig"))
    probes = probe_doc.get("probes") or []
    if args.max_probes > 0:
        probes = probes[: args.max_probes]

    rows = [
        _synthesize_probe(
            p,
            key=key or "",
            registry=registry,
            max_snippet_chars=args.max_snippet_chars,
            max_tokens=args.max_tokens,
            dry_run=args.dry_run,
        )
        for p in probes
        if isinstance(p, dict)
    ]
    ok_n = sum(1 for r in rows if r.get("status") in ("ok", "ok_non_json", "dry_run_skipped"))
    model = next((r.get("model") for r in rows if r.get("model")), None)
    doc = {
        "schema": "ng40_de_probe_nim_synthesis_v1",
        "generated_at_utc": _utc(),
        "provider": "nvidia_nim",
        "model": model,
        "hypo_label": "[HYPO]",
        "research_only": True,
        "gating": "NON_GATING",
        "probe_pointer": str(args.probe_json),
        "syntheses": rows,
        "summary": {
            "probes": len(rows),
            "ok": ok_n,
            "next": "commander_signoff_before_lut_codec",
        },
        "forbidden": ["track_a_promotion", "live_trading_gating", "auto_codec_wire"],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc["summary"], ensure_ascii=False))
    print(f"wrote {args.out_json}")
    return 0 if ok_n == len(rows) else 3


if __name__ == "__main__":
    raise SystemExit(main())
