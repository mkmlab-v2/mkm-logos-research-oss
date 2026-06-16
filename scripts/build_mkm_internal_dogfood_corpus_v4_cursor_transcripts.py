#!/usr/bin/env python3
"""Build cursor-transcript-based internal dogfood corpus (Tactical A v4).

Local-only research corpus:
- Reads agent transcript JSONL files under Cursor transcript folder
- Extracts only text message blocks (no tool-use payloads)
- Scrubs paths/emails/URLs/tokens
- Emits 20-30 rows for compression dogfood intake rehearsal
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRANSCRIPT_ROOT = Path(r"C:\Users\PRO\.cursor\projects\c-workspace\agent-transcripts")
DEFAULT_OUT = ROOT / "data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl"
META_OUT = ROOT / "reports/mkm_internal_dogfood_corpus_build_v4_cursor_transcripts_latest.json"

_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"']+")
_UNIX_PATH_RE = re.compile(r"/(?:workspace|home|Users)/[^\s\"']+")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_URL_RE = re.compile(r"https?://[^\s\"']+")
_TOKEN_RE = re.compile(r"\b(?:sk|ghp|xoxb|xoxp|AKIA)[A-Za-z0-9_\-]{8,}\b")
_ORDER_RE = re.compile(r"orderId=\d+", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scrub(text: str) -> str:
    s = text
    s = _PATH_RE.sub("[PATH]", s)
    s = _UNIX_PATH_RE.sub("[PATH]", s)
    s = _EMAIL_RE.sub("[EMAIL]", s)
    s = _URL_RE.sub("[URL]", s)
    s = _TOKEN_RE.sub("[TOKEN]", s)
    s = _ORDER_RE.sub("orderId=[REDACTED]", s)
    for old in ("C:\\workspace", "C:/workspace", "c:/workspace"):
        s = s.replace(old, "[WORKSPACE]")
    return s.strip()


def _discover_transcript_jsonl(transcript_root: Path) -> Path:
    files = sorted(transcript_root.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No transcript jsonl found under: {transcript_root}")
    return files[0]


def _extract_text_blocks(obj: dict[str, Any]) -> list[str]:
    message = obj.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    out: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        t = text.strip()
        if not t:
            continue
        out.append(t)
    return out


def _load_transcript_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _row(text: str, *, role: str, source: str, idx: int) -> dict[str, Any]:
    return {
        "text": _scrub(text),
        "domain_tag": "cursor_transcript",
        "source": source,
        "role": role,
        "dogfood": True,
        "dogfood_version": "v4_cursor_transcripts",
        "pii_scrubbed": True,
        "entry_id": f"cursor-v4-{idx:03d}",
    }


def build_corpus(
    *,
    transcript_jsonl: Path,
    min_rows: int = 20,
    target_rows: int = 24,
    max_rows: int = 30,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if target_rows < min_rows or target_rows > max_rows:
        raise ValueError(f"target_rows must be in [{min_rows}, {max_rows}]")

    events = _load_transcript_lines(transcript_jsonl)
    collected: list[dict[str, Any]] = []
    seen: set[str] = set()

    for event in events:
        role = str(event.get("role") or "unknown")
        for block in _extract_text_blocks(event):
            # Skip instruction wrappers that are noise for compression behavior.
            if "<user_query>" in block and "</user_query>" in block:
                continue
            cleaned = _scrub(block)
            if len(cleaned) < 60:
                continue
            key = cleaned[:180]
            if key in seen:
                continue
            seen.add(key)
            collected.append(_row(cleaned, role=role, source=transcript_jsonl.name, idx=len(collected)))
            if len(collected) >= target_rows:
                break
        if len(collected) >= target_rows:
            break

    if len(collected) < min_rows:
        need = min_rows - len(collected)
        for i in range(need):
            collected.append(
                _row(
                    (
                        "[CURSOR-DOGFOOD] fallback padded internal transcript row "
                        f"seq={i} send_gate=HOLD research_only=true"
                    ),
                    role="system",
                    source="synthetic_pad",
                    idx=len(collected),
                )
            )

    out_rows = collected[: max(min_rows, min(target_rows, len(collected)))]
    role_counts: dict[str, int] = {}
    for r in out_rows:
        role = str(r.get("role") or "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1

    meta = {
        "schema": "mkm_internal_dogfood_corpus_build_v4_cursor_transcripts",
        "generated_at_utc": _utc(),
        "row_count": len(out_rows),
        "source_transcript": str(transcript_jsonl),
        "role_counts": role_counts,
        "labels": [
            "dogfood",
            "internal_ops",
            "cursor_transcript",
            "pii_scrubbed",
            "research_only",
            "git_commit_forbidden",
        ],
        "tenant_recommendation": "mkm-internal-dogfood-v4-cursor",
        "one_click": (
            "py scripts/build_mkm_internal_dogfood_corpus_v4_cursor_transcripts.py "
            "&& powershell -File scripts/Run-CompressionCustomerPilotIntake_v1.ps1 "
            "-TenantId mkm-internal-dogfood-v4-cursor "
            "-CustomerJsonl data/compression/mkm_internal_dogfood_v4_cursor_transcripts.jsonl "
            "-MaxCases 24 -RelaxPassGate"
        ),
    }
    return out_rows, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transcript-root", type=Path, default=DEFAULT_TRANSCRIPT_ROOT)
    ap.add_argument("--transcript-jsonl", type=Path, default=None)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=META_OUT)
    ap.add_argument("--rows", type=int, default=24)
    args = ap.parse_args()

    transcript = args.transcript_jsonl or _discover_transcript_jsonl(args.transcript_root)
    rows, meta = build_corpus(transcript_jsonl=transcript, target_rows=args.rows)

    out = args.out_jsonl if args.out_jsonl.is_absolute() else ROOT / args.out_jsonl
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    meta["out_jsonl"] = str(out.relative_to(ROOT)).replace("\\", "/")
    meta_path = args.meta_json if args.meta_json.is_absolute() else ROOT / args.meta_json
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows),
                "out_jsonl": meta["out_jsonl"],
                "source_transcript": meta["source_transcript"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if len(rows) >= 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())

