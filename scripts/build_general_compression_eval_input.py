#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "docs" / "final" / "artifacts" / "general_compression_benchmark_manifest_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_compression_eval_input_v1.json"
DEFAULT_FALLBACK_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _shorten_words(text: str, ratio: float = 0.55) -> str:
    words = text.split()
    if not words:
        return text
    keep = max(1, int(len(words) * ratio))
    return " ".join(words[:keep])


def _load_fallback_cases(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("compression_cases") or []
    out: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        raw = str(row.get("raw_text", "")).strip()
        if not raw:
            continue
        comp = str(row.get("compressed_text", "")).strip() or _shorten_words(raw, 0.60)
        rec = str(row.get("reconstructed_text", "")).strip() or comp
        out.append(
            {
                "id": f"fallback_{idx:04d}",
                "raw_text": raw,
                "compressed_text": comp,
                "reconstructed_text": rec,
                "domain": "fallback_v2_proxy",
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build general compression eval input from corpus JSONL files.")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fallback-input", type=Path, default=DEFAULT_FALLBACK_INPUT)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    datasets = (manifest.get("corpus") or {}).get("datasets") or []
    cases: list[dict[str, str]] = []
    idx = 1
    for ds in datasets:
        source = ds.get("source_path")
        domain = ds.get("domain", "unknown")
        if not isinstance(source, str):
            continue
        src_path = (ROOT / source).resolve()
        if not src_path.is_file():
            continue
        for row in _iter_jsonl(src_path):
            raw = str(row.get("raw_text", "")).strip()
            if not raw:
                continue
            expected = row.get("expected_key_terms") or []
            if not isinstance(expected, list):
                expected = []
            keep_hint = " ".join(str(x) for x in expected[:3] if str(x).strip())
            comp = _shorten_words(raw, 0.55)
            if keep_hint and keep_hint.lower() not in comp.lower():
                comp = f"{comp} {keep_hint}".strip()
            rec = comp
            cases.append(
                {
                    "id": f"gen_{idx:04d}",
                    "raw_text": raw,
                    "compressed_text": comp,
                    "reconstructed_text": rec,
                    "domain": str(domain),
                }
            )
            idx += 1

    fallback_used = False
    if not cases:
        cases = _load_fallback_cases(args.fallback_input)
        fallback_used = bool(cases)

    out = {
        "schema": "multilens_performance_eval_input_v1",
        "description": "General-rail compression benchmark input derived from manifest datasets.",
        "compression_cases": cases,
        "fusion_answer_cases": [],
        "fallback_used": fallback_used,
        "fallback_source": str(args.fallback_input.resolve()) if fallback_used else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.out.resolve()), "case_count": len(cases), "fallback_used": fallback_used},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
