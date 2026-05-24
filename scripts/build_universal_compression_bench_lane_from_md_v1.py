#!/usr/bin/env python3
"""Harvest Universal Matrix lane eval input from markdown (B-track; not Golden 40)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


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


def _collect_paths(manifest: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for ds in manifest.get("datasets") or []:
        if isinstance(ds, dict) and ds.get("source_path"):
            paths.append(ROOT / str(ds["source_path"]))
    for glob_key in ("builtin_glob", "builtin_glob_extra"):
        globs = manifest.get(glob_key)
        if isinstance(globs, str):
            globs = [globs]
        if not isinstance(globs, list):
            continue
        for glob_rel in globs:
            if not isinstance(glob_rel, str) or not glob_rel.strip():
                continue
            g = ROOT / glob_rel
            paths.extend(sorted(p for p in g.parent.glob(g.name) if p.is_file()))
    exclude: set[Path] = set()
    for eg in manifest.get("exclude_globs") or []:
        if not isinstance(eg, str):
            continue
        g = ROOT / eg
        exclude.update(p.resolve() for p in g.parent.glob(g.name) if p.is_file())
    seen: set[Path] = set()
    ordered: list[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp in seen or rp in exclude:
            continue
        seen.add(rp)
        ordered.append(p)
    return ordered


def _build_cases(
    md_paths: list[Path],
    *,
    id_prefix: str,
    domain: str,
    min_chars: int,
    max_cases: int,
) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    idx = 1
    for md_path in md_paths:
        if not md_path.is_file():
            continue
        text = md_path.read_text(encoding="utf-8", errors="replace")
        for para in _extract_paragraphs(text, min_chars=min_chars):
            comp = _shorten_words(para, 0.55)
            cases.append(
                {
                    "id": f"{id_prefix}_{idx:04d}",
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    manifest_path = (ROOT / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out_path = (ROOT / args.out).resolve() if not args.out.is_absolute() else args.out.resolve()
    domain = str(manifest.get("domain_tag") or "unknown")
    id_prefix = str(manifest.get("id_prefix") or domain.replace("_", "")[:8])
    min_chars = int((manifest.get("paragraph_rules") or {}).get("min_chars") or 80)
    max_cases = int(manifest.get("max_cases") or 100)
    paths = _collect_paths(manifest)
    cases = _build_cases(
        paths,
        id_prefix=id_prefix,
        domain=domain,
        min_chars=min_chars,
        max_cases=max(1, max_cases),
    )

    out_doc = {
        "schema": "multilens_performance_eval_input_v1",
        "description": f"Universal Matrix lane {manifest.get('lane_id')} from markdown harvest.",
        "research_only": True,
        "boundary_ack": manifest.get("boundary_ack"),
        "compression_cases": cases,
        "domain_tag": domain,
        "lane_id": manifest.get("lane_id"),
        "source_manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "case_count": len(cases),
                "domain": domain,
            },
            ensure_ascii=False,
        )
    )
    return 0 if cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
