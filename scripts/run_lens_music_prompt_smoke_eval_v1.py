#!/usr/bin/env python3
"""M21 smoke eval for dynamic prompt overlay style alignment."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLES = ROOT / "tests" / "fixtures" / "lens_music_prompt_smoke_eval_sample_v1.jsonl"
DEFAULT_OUT = ROOT / "reports" / "lens_music_prompt_smoke_eval_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sent_count(text: str) -> int:
    parts = re.split(r"[.!?]\s+|[.!?]$", text.strip())
    return len([p for p in parts if p.strip()])


def _style_match(text: str, style: str) -> bool:
    t = text.strip()
    if style == "bright_concise":
        return _sent_count(t) <= 2
    if style == "calm_guarded":
        return _sent_count(t) <= 3 and ("보수" in t or "차분" in t or "주의" in t)
    if style == "empathetic_reflective":
        return _sent_count(t) >= 1 and ("정리" in t or "단계" in t or "안정" in t)
    return False


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples-jsonl", type=Path, default=DEFAULT_SAMPLES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.samples_jsonl)
    judged = []
    hit = 0
    for r in rows:
        text = str(r.get("response_text") or "")
        meta = dict(r.get("meta") or {})
        style = str(meta.get("answer_style") or "")
        ok = _style_match(text, style)
        if ok:
            hit += 1
        judged.append(
            {
                "answer_style": style,
                "sentence_length": meta.get("sentence_length"),
                "sent_count": _sent_count(text),
                "match": ok,
            }
        )

    total = len(judged)
    score = (hit / total) if total else 0.0
    state = "GO" if score >= 0.67 else "WATCH"
    out = {
        "schema": "lens_music_prompt_smoke_eval_v1",
        "generated_at_utc": _utc_now(),
        "samples_count": total,
        "style_match_count": hit,
        "style_match_rate": round(score, 6),
        "state": state,
        "rows": judged,
        "note": "M21 smoke-only heuristic eval; advisory and non-blocking.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": state, "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
