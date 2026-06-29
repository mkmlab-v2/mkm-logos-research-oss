#!/usr/bin/env python3
"""Lint 창업패키지 340 paste_ready pack before docx fill (pre-flight)."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
OUT = ROOT / "reports/kstartup_startup_package_ai_paste_lint_latest.json"

REQUIRED: tuple[tuple[str, int], ...] = (
    ("plan_01_summary_paste.txt", 120),
    ("plan_02_market_problem_paste.txt", 200),
    ("plan_03_tech_roadmap_paste.txt", 400),
    ("plan_04_growth_funding_paste.txt", 280),
    ("plan_05_team_paste.txt", 180),
    ("plan_06_ai_talent_2p_paste.txt", 200),
)

HEADING_RE = re.compile(r"^\s*(\d+\.\d+)\s+(\S+)", re.MULTILINE)
HIRE_MONTH_RE = re.compile(r"'(?:2[56])\.\d{2}")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strip_header(raw: str) -> str:
    raw = re.sub(r"^\[창업패키지[^\]]*\]\s*\n+", "", raw)
    return raw.strip()


def _duplicate_headings(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    labels = HEADING_RE.findall(text)
    counts = Counter(labels)
    for (num, title), n in counts.items():
        if n > 1:
            hits.append({"heading": f"{num} {title}", "count": n})
    return hits


def _duplicate_paragraphs(text: str, *, min_len: int = 80) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    norm = [re.sub(r"\s+", " ", p) for p in paras if len(p) >= min_len]
    counts = Counter(norm)
    return [p[:100] + "…" if len(p) > 100 else p for p, n in counts.items() if n > 1]


def _hire_month_tags(text: str) -> list[str]:
    return sorted(set(HIRE_MONTH_RE.findall(text)))


def lint_paste_dir(paste_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    files: dict[str, Any] = {}

    for fname, min_chars in REQUIRED:
        path = paste_dir / fname
        if not path.is_file():
            errors.append(f"missing:{fname}")
            files[fname] = {"ok": False, "reason": "missing"}
            continue
        body = _strip_header(path.read_text(encoding="utf-8"))
        n = len(body)
        dup_h = _duplicate_headings(body)
        dup_p = _duplicate_paragraphs(body)
        hire = _hire_month_tags(body) if fname == "plan_06_ai_talent_2p_paste.txt" else []
        ok = n >= min_chars and not dup_h
        files[fname] = {
            "ok": ok,
            "chars": n,
            "min_chars": min_chars,
            "duplicate_headings": dup_h,
            "duplicate_paragraphs": dup_p[:5],
            "hire_month_tags": hire,
        }
        if n < min_chars:
            errors.append(f"thin:{fname}:{n}<{min_chars}")
        if dup_h:
            errors.append(f"duplicate_heading:{fname}:{dup_h[0]['heading']}")
        if dup_p:
            warnings.append(f"duplicate_paragraph:{fname}:{len(dup_p)}")

    combined = "\n\n".join(
        _strip_header((paste_dir / fname).read_text(encoding="utf-8"))
        for fname, _ in REQUIRED
        if (paste_dir / fname).is_file()
    )
    cross_dup = _duplicate_headings(combined)
    if cross_dup:
        for item in cross_dup:
            errors.append(f"duplicate_heading_combined:{item['heading']}:{item['count']}")

    all_hire = sorted(set(HIRE_MONTH_RE.findall(combined)))
    if len(all_hire) >= 3:
        warnings.append(f"hire_month_tags_many:{','.join(all_hire)}")

    if "OpenData" not in combined and "공공데이터" not in combined:
        warnings.append("opendata_keyword_absent")

    try:
        paste_rel = str(paste_dir.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        paste_rel = str(paste_dir)

    return {
        "schema": "kstartup_startup_package_ai_paste_lint_v1",
        "generated_at_utc": _utc(),
        "paste_dir": paste_rel,
        "files": files,
        "combined_hire_month_tags": all_hire,
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
        "strict_ok": not errors and not warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint 340 paste_ready before fill.")
    ap.add_argument("--paste-dir", default=str(PASTE_DIR))
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    report = lint_paste_dir(Path(args.paste_dir))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        return 1
    if args.strict and report["warnings"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
