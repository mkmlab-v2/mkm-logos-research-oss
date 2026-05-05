#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(" ,.;:") + "."


def normalize_lines(md: str) -> str:
    lines = [ln.rstrip() for ln in md.splitlines()]
    out: list[str] = []
    blank = False
    for ln in lines:
        if ln.strip() == "":
            if not blank:
                out.append("")
            blank = True
            continue
        out.append(ln)
        blank = False
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"


def section(md: str, header: str) -> str:
    key = f"## {header}"
    lines = md.splitlines()
    start = -1
    for i, ln in enumerate(lines):
        if ln.strip() == key:
            start = i + 1
            break
    if start < 0:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Polish camera-ready markdown to submission-friendly normalized form.")
    ap.add_argument("--paper-in-md", default="docs/final/artifacts/global_atom_camera_ready_paper_draft_latest.md")
    ap.add_argument("--appendix-in-md", default="docs/final/artifacts/global_atom_camera_ready_appendix_latest.md")
    ap.add_argument("--paper-out-md", default="docs/final/artifacts/global_atom_camera_ready_paper_polished_latest.md")
    ap.add_argument("--appendix-out-md", default="docs/final/artifacts/global_atom_camera_ready_appendix_polished_latest.md")
    ap.add_argument("--manifest-out-json", default="docs/final/artifacts/global_atom_camera_ready_polish_latest.json")
    args = ap.parse_args()

    paper_in = resolve(args.paper_in_md)
    app_in = resolve(args.appendix_in_md)
    if not paper_in.is_file() or not app_in.is_file():
        raise SystemExit("missing camera-ready draft inputs")

    paper = normalize_lines(paper_in.read_text(encoding="utf-8"))
    app = normalize_lines(app_in.read_text(encoding="utf-8"))

    abstract = section(paper, "Abstract")
    if abstract:
        paper = paper.replace(abstract, trim_words(abstract, 170))

    method = section(paper, "Method")
    if method:
        method_lines = [ln for ln in method.splitlines() if ln.strip()]
        method_lines = method_lines[:4]
        paper = paper.replace(method, "\n".join(method_lines))

    risks = section(paper, "Risks")
    if risks:
        risk_lines = [ln for ln in risks.splitlines() if ln.strip()]
        risk_lines = risk_lines[:3]
        paper = paper.replace(risks, "\n".join(risk_lines))

    paper_out = resolve(args.paper_out_md)
    app_out = resolve(args.appendix_out_md)
    manifest_out = resolve(args.manifest_out_json)
    paper_out.parent.mkdir(parents=True, exist_ok=True)
    paper_out.write_text(normalize_lines(paper), encoding="utf-8")
    app_out.write_text(normalize_lines(app), encoding="utf-8")

    manifest = {
        "schema": "global_atom_camera_ready_polish_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {"paper_in_md": str(paper_in), "appendix_in_md": str(app_in)},
        "outputs": {"paper_out_md": str(paper_out), "appendix_out_md": str(app_out)},
        "polish_rules": {
            "abstract_max_words": 170,
            "method_max_bullets": 4,
            "risk_max_bullets": 3,
            "blank_line_normalization": True,
        },
    }
    manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(manifest_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

