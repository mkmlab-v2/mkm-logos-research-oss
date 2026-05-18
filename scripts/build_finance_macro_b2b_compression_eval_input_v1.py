#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.88, K:0.62, M:0.48}
# Balance: 90
# Purpose: Build finance/macro Track C B2B compression eval input from markdown corpora.
# Keywords: track_c, compression, finance_macro_b2b, multilens_performance_eval_input_v1
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (
    ROOT / "docs" / "final" / "artifacts" / "finance_macro_b2b_compression_benchmark_manifest_v1.json"
)
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "finance_macro_b2b_compression_eval_input_v1.json"
DEFAULT_DOMAIN = "finance_macro_b2b"
DEFAULT_MIN_CHARS = 80
DEFAULT_MAX_CASES = 200
DEFAULT_MD_GLOB = "docs/final/artifacts/track_c_b2b_macro*.md"


def _shorten_words(text: str, ratio: float = 0.55) -> str:
    words = text.split()
    if not words:
        return text
    keep = max(1, int(len(words) * ratio))
    return " ".join(words[:keep])


def _extract_paragraphs(text: str, *, min_chars: int) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", text)
    out: list[str] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue
        if all(ln.startswith("#") for ln in lines):
            continue
        para = " ".join(lines)
        if len(para) < min_chars:
            continue
        out.append(para)
    return out


def _default_md_paths() -> list[Path]:
    pattern = ROOT / DEFAULT_MD_GLOB
    return sorted(p for p in pattern.parent.glob(pattern.name) if p.is_file())


def _paths_from_manifest(manifest: dict[str, Any]) -> list[Path]:
    corpus = manifest.get("corpus") or {}
    domain_default = str(corpus.get("domain_tag") or DEFAULT_DOMAIN)
    paths: list[Path] = []
    for ds in corpus.get("datasets") or []:
        if not isinstance(ds, dict):
            continue
        source = ds.get("source_path")
        if not isinstance(source, str) or not source.strip():
            continue
        paths.append((ROOT / source).resolve())
    if paths:
        return paths
    glob_rel = corpus.get("builtin_default_glob")
    if isinstance(glob_rel, str) and glob_rel.strip():
        g = ROOT / glob_rel
        return sorted(p for p in g.parent.glob(g.name) if p.is_file())
    return _default_md_paths()


def _resolve_sources(manifest_path: Path | None) -> tuple[list[Path], str, int]:
    if manifest_path is not None and manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        corpus = manifest.get("corpus") or {}
        domain = str(corpus.get("domain_tag") or DEFAULT_DOMAIN)
        min_chars = int((corpus.get("paragraph_rules") or {}).get("min_chars") or DEFAULT_MIN_CHARS)
        paths = _paths_from_manifest(manifest)
        return paths, domain, min_chars
    return _default_md_paths(), DEFAULT_DOMAIN, DEFAULT_MIN_CHARS


def _build_cases(
    md_paths: list[Path],
    *,
    domain: str,
    min_chars: int,
    max_cases: int,
) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    idx = 1
    for md_path in md_paths:
        if not md_path.is_file():
            continue
        text = md_path.read_text(encoding="utf-8")
        for para in _extract_paragraphs(text, min_chars=min_chars):
            comp = _shorten_words(para, 0.55)
            cases.append(
                {
                    "id": f"fin_b2b_{idx:04d}",
                    "raw_text": para,
                    "compressed_text": comp,
                    "reconstructed_text": comp,
                    "domain": domain,
                    "source_path": str(md_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
            idx += 1
            if len(cases) >= max_cases:
                return cases
    return cases


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build finance/macro B2B compression eval input from Track C markdown sources.",
    )
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cases", type=int, default=DEFAULT_MAX_CASES)
    ap.add_argument("--dry-run", action="store_true", help="Print summary JSON to stdout; do not write --out")
    args = ap.parse_args()

    manifest_path = args.manifest if args.manifest.is_file() else None
    md_paths, domain, min_chars = _resolve_sources(manifest_path)
    cases = _build_cases(
        md_paths,
        domain=domain,
        min_chars=min_chars,
        max_cases=max(1, args.max_cases),
    )

    summary = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "out": str(args.out.resolve()),
        "case_count": len(cases),
        "domain": domain,
        "min_chars": min_chars,
        "max_cases": args.max_cases,
        "md_files_requested": len(md_paths),
        "md_files_found": sum(1 for p in md_paths if p.is_file()),
        "manifest": str(args.manifest.resolve()) if manifest_path else None,
        "used_builtin_default": manifest_path is None,
    }

    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    out_doc = {
        "schema": "multilens_performance_eval_input_v1",
        "description": "Finance/macro Track C B2B compression benchmark input from markdown paragraph extraction.",
        "compression_cases": cases,
        "fusion_answer_cases": [],
        "source_manifest": str(args.manifest.resolve()) if manifest_path else None,
        "domain_tag": domain,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["schema"] = out_doc["schema"]
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
