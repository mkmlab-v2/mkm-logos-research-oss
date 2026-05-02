#!/usr/bin/env python3
"""로고스(Logos) 독립 렌즈 v0: verse 4D 샘플 배치 → 정량 스코어 (근원·금융 레짐 미혼합)."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH = ROOT / "data" / "logos" / "4lens_batch_sample.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"

ARTIFACT_SCHEMA = "logos_independent_lens_v0"
ENGINE_ID = "independent_lens_v0"
VERSION = "0.2.0"

MAX_PER_VERSE_SNIPPET = 160
MAX_NARRATIVE_GUARD_CHARS = 2000


def _clip_text(s: str, n: int) -> str:
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def _verse_id_from_item(item: dict[str, Any]) -> str | None:
    for key in ("verse_id", "verse_ref", "canonical_ref", "ref"):
        v = item.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    meta = item.get("metadata")
    if isinstance(meta, dict):
        for key in ("verse_id", "verse_ref"):
            v = meta.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    vid = item.get("id")
    if isinstance(vid, str) and vid.strip():
        return vid.strip()
    return None


def _verse_text_from_item(item: dict[str, Any]) -> str | None:
    for key in ("verse_text", "verse_plain", "text_utf8", "text", "surface_text", "decoded_text"):
        v = item.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    p1 = item.get("pipeline1_simple_4d")
    if isinstance(p1, dict):
        for key in ("verse_snippet", "surface"):
            v = p1.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _quote_hash(text: str | None) -> str | None:
    if not text:
        return None
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _hash_tagged_snippet(verse_id: str | None, text: str | None) -> str:
    tag = verse_id if verse_id else "?"
    body = _clip_text(text, MAX_PER_VERSE_SNIPPET) if text else ""
    if body:
        return f"[#{tag}] {body}"
    return f"[#{tag}]"


def _build_narrative_guarded(evidence_refs: list[dict[str, Any]]) -> str | None:
    parts: list[str] = []
    for row in evidence_refs:
        s = row.get("hash_tagged_snippet")
        if isinstance(s, str) and s.strip():
            parts.append(s.strip())
    if not parts:
        return None
    joined = " ".join(parts)
    if len(joined) <= MAX_NARRATIVE_GUARD_CHARS:
        return joined
    return joined[: MAX_NARRATIVE_GUARD_CHARS - 1].rstrip() + "…"


def _mean_4d_from_item(item: dict[str, Any]) -> dict[str, float] | None:
    p1 = item.get("pipeline1_simple_4d")
    if not isinstance(p1, dict):
        return None
    v4 = p1.get("vector_4d")
    if not isinstance(v4, dict):
        return None
    out: dict[str, float] = {}
    for k in ("S", "L", "K", "M"):
        x = v4.get(k)
        if isinstance(x, (int, float)):
            out[k] = float(x)
    return out if len(out) == 4 else None


def _aggregate_batch(path: Path) -> tuple[list[dict[str, float]], int, list[dict[str, Any]]]:
    if not path.is_file():
        return [], 0, []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], 0, []
    if not isinstance(doc, list):
        return [], 0, []
    vecs: list[dict[str, float]] = []
    evidence_refs: list[dict[str, Any]] = []
    for item in doc:
        if not isinstance(item, dict):
            continue
        m = _mean_4d_from_item(item)
        if m:
            vecs.append(m)
            vid = _verse_id_from_item(item)
            vtxt = _verse_text_from_item(item)
            evidence_refs.append(
                {
                    "verse_id": vid,
                    "quote_hash": _quote_hash(vtxt),
                    "hash_tagged_snippet": _hash_tagged_snippet(vid, vtxt),
                }
            )
    return vecs, len(doc), evidence_refs


def _scores_from_vecs(vecs: list[dict[str, float]]) -> tuple[float, float]:
    if not vecs:
        return 0.0, 0.25
    acc = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    for v in vecs:
        for k in acc:
            acc[k] += v[k]
    n = float(len(vecs))
    mean_all = sum(acc[k] / n for k in acc) / 4.0
    direction = max(-1.0, min(1.0, (mean_all - 0.5) * 2.0))
    conf = min(1.0, max(0.2, len(vecs) / 20.0))
    return round(direction, 6), round(conf, 6)


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit logos independent lens v0 JSON from 4D batch sample.")
    ap.add_argument("--batch-json", type=Path, default=DEFAULT_BATCH)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow empty fallback payload when no 4D vectors are available.",
    )
    args = ap.parse_args()

    vecs, total_rows, evidence_refs = _aggregate_batch(args.batch_json)
    if not vecs and not args.allow_fallback:
        print(
            "logos lens hard-gate: no pipeline1_simple_4d vectors found "
            f"(input={args.batch_json}). Use --allow-fallback only for manual debugging."
        )
        return 2
    direction, conf = _scores_from_vecs(vecs)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    narrative_guarded = _build_narrative_guarded(evidence_refs) if vecs else None

    payload = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "lens_id": "logos",
        "engine_id": ENGINE_ID,
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "scores": {
            "direction_score": direction,
            "confidence": conf,
        },
        "evidence_refs": evidence_refs if vecs else [],
        "narrative_snippet_guarded": narrative_guarded,
        "snippet_guard_policy": "Only hash-tagged lines [#verse_id] + optional clipped verse_text from batch; no model paraphrase.",
        "logos_stream_outputs": {
            "source_batch_path": str(args.batch_json.resolve()),
            "verses_with_simple_4d": len(vecs),
            "batch_rows_total": total_rows,
            "evidence_row_count": len(evidence_refs),
            "rationale": "Mean of pipeline1_simple_4d vector_4d over batch; Logos root only — no regime/KOSPI mixed in this runner.",
        },
        "provenance": {
            "source": "4lens_batch_json" if vecs else "empty_fallback",
            "input_path": str(args.batch_json.resolve()),
        },
        "note": "Logos First: verse 4D only; not a market forecast; fusion-ready numeric stub.",
    }
    if not vecs:
        payload["scores"] = {"direction_score": 0.0, "confidence": 0.2}
        payload["logos_stream_outputs"]["rationale"] = "No pipeline1_simple_4d vectors; empty fallback."

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
