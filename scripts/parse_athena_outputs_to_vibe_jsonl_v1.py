#!/usr/bin/env python3
"""Parse Athena raw outputs into Vibe model output JSONL format."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
IN_DIR = ART / "vibe_runs_raw" / "athena_raw_outputs"
OUT_JSONL = ART / "vibe_runs_raw" / "vibe_model_outputs_latest.jsonl"
RUNS_JSONL = ART / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"

DECISIONS = frozenset({"HOLD", "REDUCE", "WATCH"})


def load_expected_slots(path: Path) -> set[tuple[str, int]]:
    if not path.is_file():
        return set()
    expected: set[tuple[str, int]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        pid = str(obj.get("prompt_id"))
        rid = int(obj.get("run_index"))
        expected.add((pid, rid))
    return expected


def parse_decision(text: str) -> str | None:
    """Prefer explicit Final Action / JSON decision; else earliest keyword in body."""
    m = re.search(
        r"(?im)^\s*(?:final\s*action|decision)\s*[:=]\s*(HOLD|REDUCE|WATCH)\b",
        text,
    )
    if m:
        return m.group(1).upper()
    m_json = re.search(
        r"""["']decision["']\s*:\s*["']?(HOLD|REDUCE|WATCH)["']?""",
        text,
        flags=re.IGNORECASE,
    )
    if m_json:
        return m_json.group(1).upper()
    upper = text.upper()
    best: str | None = None
    best_pos = 10**9
    for d in ("HOLD", "REDUCE", "WATCH"):
        hit = re.search(rf"\b{d}\b", upper)
        if hit and hit.start() < best_pos:
            best_pos = hit.start()
            best = d
    return best


def parse_confidence(text: str) -> float | None:
    m = re.search(r"(?:confidence|신뢰도)\s*[:=]?\s*([01](?:\.\d+)?)", text, flags=re.IGNORECASE)
    if m:
        try:
            v = float(m.group(1))
            return v if 0.0 <= v <= 1.0 else None
        except ValueError:
            return None
    return None


def parse_risk_flags(text: str) -> list[str]:
    flags: list[str] = []
    for kw in ["overfit", "hallucination", "stale", "low_evidence", "conflict", "volatility"]:
        if kw in text.lower():
            flags.append(kw)
    return flags


def parse_meta_from_filename(path: Path) -> tuple[str, int] | None:
    # Expected filename pattern: prompt_01_run_03.md/.txt
    m = re.match(r"^(prompt_\d{2})_run_(\d+)\.(?:md|txt)$", path.name, flags=re.IGNORECASE)
    if not m:
        return None
    return m.group(1).lower(), int(m.group(2))


def parse_file(path: Path) -> dict[str, Any] | None:
    meta = parse_meta_from_filename(path)
    if not meta:
        return None
    prompt_id, run_index = meta
    text = path.read_text(encoding="utf-8", errors="ignore")
    upper = text.upper()
    # Skip untouched slot templates.
    if "FINAL ACTION: HOLD|REDUCE|WATCH" in upper:
        return None

    decision = parse_decision(text)
    confidence = parse_confidence(text)
    risk_flags = parse_risk_flags(text)
    rationale_short = "parsed_from_athena_raw_output"

    if decision not in DECISIONS:
        # Skip non-decodable outputs to avoid false positive ingestion.
        return None

    return {
        "prompt_id": prompt_id,
        "run_index": run_index,
        "decision": decision,
        "confidence": confidence,
        "rationale_short": rationale_short,
        "risk_flags": risk_flags,
        "raw_output_path": str(path).replace("\\", "/"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default=str(IN_DIR))
    parser.add_argument("--output-jsonl", type=str, default=str(OUT_JSONL))
    parser.add_argument("--runs-jsonl", type=str, default=str(RUNS_JSONL))
    parser.add_argument(
        "--filter-to-runs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only parse files that correspond to rows in vibe_prompt_runs_latest.jsonl (recommended).",
    )
    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_path = Path(args.output_jsonl)
    runs_path = Path(args.runs_jsonl)
    in_dir.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    expected = load_expected_slots(runs_path) if args.filter_to_runs else set()

    files = sorted([p for p in in_dir.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".txt"}])
    rows: list[dict[str, Any]] = []
    skipped = 0
    for p in files:
        meta = parse_meta_from_filename(p)
        if expected and meta:
            prompt_id, run_index = meta
            if (prompt_id, run_index) not in expected:
                skipped += 1
                continue
        row = parse_file(p)
        if row is None:
            skipped += 1
            continue
        rows.append(row)

    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"parsed_files: {len(rows)}")
    print(f"skipped_files: {skipped}")
    print(f"written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

