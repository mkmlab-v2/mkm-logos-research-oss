#!/usr/bin/env python3
"""MKM paper digest v1: PDF/txt → Tier0 md → digestion chain (B-track).

Trigger word (commander): 소화 · 논문 소화 · digest paper
research_only · send_gate HOLD · no Track A / [CANON] auto-promotion
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW = ROOT / "docs/research/raw"
ARTIFACTS = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports/constitution/btrack_pilot"
HAAN_INDEX = REPORTS / "haan_library_downloads_batch_v1_latest.json"
DIGEST_CHAIN = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
MIN_EXTRACT_CHARS = 80

from scripts.extract_lens_coordinate_facts_v1 import (  # noqa: E402
    coordinate_facts_to_markdown,
    extract_coordinate_facts,
)
from scripts.mkm_paper_ocr_extract_v1 import extract_pdf_text  # noqa: E402
from scripts.mkm_dr2_digest_wiring_v1 import count_silent_unwired  # noqa: E402

LENS_NON_GATING = {"logos": "[NON_GATING]", "myeongri": "[HYPO]", "ijeoma": "[HYPO]"}

SECTION_MARKERS = [
    ("abstract", re.compile(r"(?:^|\n)\s*(?:초록|요약|Abstract)\s*[:：]?\s*", re.I)),
    ("purpose", re.compile(r"(?:^|\n)\s*(?:연구\s*목적|목적|연구\s*문제|문제\s*의식)\s*[:：]?\s*", re.I)),
    ("method", re.compile(r"(?:^|\n)\s*(?:연구\s*방법|방법|연구\s*절차)\s*[:：]?\s*", re.I)),
    ("conclusion", re.compile(r"(?:^|\n)\s*(?:결론|맺음말|Conclusion)\s*[:：]?\s*", re.I)),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return (slug or "paper")[:72]


def _read_source(
    path: Path,
    *,
    ocr_backend: str = "auto",
    ocr_max_pages: int | None = 150,
) -> tuple[str, str]:
    if path.suffix.lower() == ".pdf":
        if ocr_backend == "none":
            try:
                from pdfminer.high_level import extract_text

                return (extract_text(str(path)) or "").strip(), "pdfminer.six"
            except ImportError as exc:
                raise RuntimeError("Install pdfminer.six or use --ocr-backend auto") from exc
        return extract_pdf_text(
            path,
            backend=ocr_backend,
            min_chars=MIN_EXTRACT_CHARS,
            ocr_max_pages=ocr_max_pages,
        )
    return path.read_text(encoding="utf-8", errors="replace").strip(), "plain_text"


def _slice_after(text: str, pattern: re.Pattern[str], *, max_len: int = 2500) -> str:
    m = pattern.search(text)
    if not m:
        return ""
    chunk = text[m.end() : m.end() + max_len]
    chunk = re.sub(r"\s+", " ", chunk).strip()
    return chunk[:max_len]


def _guess_title(path: Path, text: str) -> str:
    head = re.sub(r"\s+", " ", text[:800]).strip()
    if head:
        first_line = head.split("  ")[0][:200]
        if len(first_line) > 12:
            return first_line
    return path.stem.replace("_", " ")


def _key_sentences(text: str, *, limit: int = 5) -> list[str]:
    compact = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+", compact)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) < 40 or len(p) > 320:
            continue
        if p not in out:
            out.append(p)
        if len(out) >= limit:
            break
    return out


def _build_reading_digest(title: str, text: str) -> dict[str, str]:
    digest: dict[str, str] = {"title": title}
    for key, pat in SECTION_MARKERS:
        digest[key] = _slice_after(text, pat)
    if not digest.get("abstract"):
        digest["abstract"] = re.sub(r"\s+", " ", text[:1200]).strip()
    if not digest.get("conclusion"):
        digest["conclusion"] = re.sub(r"\s+", " ", text[-2000:]).strip()
    digest["key_sentences"] = "\n".join(f"- {s}" for s in _key_sentences(text))
    return digest


def _digested_facts_block(
    title: str,
    text: str,
    digest: dict[str, str],
    backend: str,
    *,
    lens: str = "",
) -> str:
    char_count = len(text)
    section_hits = sum(1 for k in ("abstract", "purpose", "method", "conclusion") if digest.get(k))
    lines = [
        "## Digested facts (MKM paper digest v1)",
        "",
        "Explicit mechanical + reading-surface facts — **not** LLM invention.",
        "",
        "### fact_id: source_text_char_count",
        "- metric_name: extracted_text_chars",
        f"- value: {char_count}",
        "- unit: count",
        f"- comparison_arm: {title[:120]}",
        "- verification_status: Unknown",
        "- verification_method: fixture_trusted",
        f"- table_ref: extract_backend={backend}",
        "",
        "### fact_id: section_marker_hits",
        "- metric_name: academic_section_markers",
        f"- value: {section_hits}",
        "- unit: count",
        f"- comparison_arm: {title[:120]}",
        "- verification_status: Unknown",
        "- verification_method: fixture_trusted",
        "",
    ]
    for i, sent in enumerate(_key_sentences(text, limit=3), start=1):
        fid = f"key_sentence_{i}"
        lines.extend(
            [
                f"### fact_id: {fid}",
                "- metric_name: semantic_claim_surface",
                "- value: 1",
                "- unit: count",
                f"- comparison_arm: {sent[:100]}",
                "- verification_status: Unknown",
                "- verification_method: abstract_only",
                "",
            ]
        )
    if lens:
        try:
            coord_facts = extract_coordinate_facts(text, lens=lens, title=title)
            coord_md = coordinate_facts_to_markdown(coord_facts)
            if coord_md:
                lines.append(coord_md)
        except (FileNotFoundError, ValueError):
            pass
    return "\n".join(lines)


def build_tier0_md(
    *,
    source_path: Path,
    lens: str,
    text: str,
    backend: str,
    sha256: str,
) -> Path:
    title = _guess_title(source_path, text)
    digest = _build_reading_digest(title, text)
    slug = _slugify(f"{lens}_{source_path.stem}")
    out = RAW / f"{slug}_PAPER_DIGEST_tier0_v1.md"
    tag = LENS_NON_GATING.get(lens, "[HYPO]")
    excerpt_cap = 48000
    excerpt = text[:excerpt_cap]
    truncated = len(text) > excerpt_cap

    body = [
        f"# Tier 0 — Paper digest · {title}",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD` · lens `{lens}` {tag}",
        f"**source_pdf:** `{source_path.relative_to(ROOT).as_posix()}`",
        f"**extract_backend:** {backend}",
        f"**sha256:** `{sha256}`",
        "",
        "## Reading digest (heuristic — verify against excerpt)",
        "",
        f"**title_guess:** {title}",
        "",
        "### abstract_or_lead",
        "",
        digest.get("abstract") or "(empty)",
        "",
        "### purpose",
        "",
        digest.get("purpose") or "(not detected)",
        "",
        "### method",
        "",
        digest.get("method") or "(not detected)",
        "",
        "### conclusion",
        "",
        digest.get("conclusion") or "(not detected)",
        "",
        "### key_sentences",
        "",
        digest.get("key_sentences") or "(none)",
        "",
        _digested_facts_block(title, text, digest, backend, lens=lens),
        "## Full text excerpt",
        "",
        "```",
        excerpt,
        "```",
        "",
    ]
    if truncated:
        body.append(f"*(truncated at {excerpt_cap} chars; full text on disk)*\n")
    out.write_text("\n".join(body), encoding="utf-8")
    return out


def run_digestion_chain(tier0: Path, *, offline: bool = True) -> tuple[int, Path]:
    chain_out = REPORTS / f"mkm_paper_digest_chain_{tier0.stem}_v1.json"
    cmd = [
        sys.executable,
        str(DIGEST_CHAIN),
        "--input",
        str(tier0.relative_to(ROOT)),
        "--out-json",
        str(chain_out.relative_to(ROOT)),
        "--skip-citation-lock",
    ]
    if offline:
        cmd.append("--offline")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return proc.returncode, chain_out


def digest_one(
    source: Path,
    *,
    lens: str,
    skip_chain: bool = False,
    ocr_backend: str = "auto",
    ocr_max_pages: int | None = 150,
) -> dict[str, Any]:
    path = source if source.is_absolute() else ROOT / source
    if not path.is_file():
        return {"ok": False, "error": f"missing: {path}", "source": str(source)}

    try:
        text, backend = _read_source(
            path,
            ocr_backend=ocr_backend,
            ocr_max_pages=ocr_max_pages,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"extract_failed: {exc}", "source": str(path)}

    if len(text.strip()) < MIN_EXTRACT_CHARS:
        return {
            "ok": False,
            "error": "extracted_text_too_short",
            "source": str(path),
            "text_chars": len(text.strip()),
            "extract_backend": backend,
        }

    sha = _sha256_file(path)
    tier0 = build_tier0_md(source_path=path, lens=lens, text=text, backend=backend, sha256=sha)
    digested_path = ARTIFACTS / f"{tier0.stem}_digested_facts_latest.json"
    result: dict[str, Any] = {
        "ok": True,
        "source": path.relative_to(ROOT).as_posix(),
        "lens": lens,
        "tier0": tier0.relative_to(ROOT).as_posix(),
        "text_chars": len(text),
        "extract_backend": backend,
        "sha256": sha,
    }

    if skip_chain:
        result["digestion_chain"] = "skipped"
        return result

    code, chain_out = run_digestion_chain(tier0)
    result["digestion_chain_exit"] = code
    result["digestion_chain_report"] = chain_out.relative_to(ROOT).as_posix()
    result["digested_facts"] = (
        digested_path.relative_to(ROOT).as_posix() if digested_path.is_file() else None
    )
    if digested_path.is_file():
        dig_doc = json.loads(digested_path.read_text(encoding="utf-8"))
        silent = count_silent_unwired(dig_doc.get("facts") or [])
        result["silent_unwired_count"] = silent
        if silent > 0:
            result["ok"] = False
            result["error"] = "silent_unbound_digest_facts_forbidden"
    if code != 0:
        result["ok"] = False
        result["error"] = result.get("error") or "digestion_chain_failed"
    elif result.get("ok") is not False:
        result["ok"] = True
    return result


def _items_for_lens(lens: str) -> list[dict[str, Any]]:
    if not HAAN_INDEX.is_file():
        return []
    doc = json.loads(HAAN_INDEX.read_text(encoding="utf-8"))
    lanes = {lens}
    if lens == "logos":
        lanes.add("ijeoma_logos_bridge")
    return [it for it in doc.get("items") or [] if it.get("lens") in lanes]


def main() -> int:
    ap = argparse.ArgumentParser(description="MKM paper digest: PDF/txt → Tier0 → digestion chain")
    ap.add_argument("--pdf", type=Path, help="Single PDF or txt path")
    ap.add_argument("--lens", choices=("logos", "myeongri", "ijeoma"), help="Digest all HAAN items for lens")
    ap.add_argument("--skip-chain", action="store_true", help="Tier0 only; skip digestion engine")
    ap.add_argument(
        "--ocr-backend",
        choices=("auto", "none", "pdfminer", "pymupdf", "rapidocr"),
        default="auto",
        help="PDF extract backend; auto tries text layer then OCR",
    )
    ap.add_argument(
        "--ocr-max-pages",
        type=int,
        default=150,
        help="Max pages for rapidocr (0 = all pages)",
    )
    ap.add_argument("--out", type=Path, default=REPORTS / "mkm_paper_digest_run_v1_latest.json")
    args = ap.parse_args()
    ocr_max_pages = None if args.ocr_max_pages == 0 else args.ocr_max_pages

    if not args.pdf and not args.lens:
        ap.error("Provide --pdf or --lens")

    results: list[dict[str, Any]] = []
    if args.pdf:
        lens = args.lens or "ijeoma"
        results.append(
            digest_one(
                args.pdf,
                lens=lens,
                skip_chain=args.skip_chain,
                ocr_backend=args.ocr_backend,
                ocr_max_pages=ocr_max_pages,
            )
        )
    else:
        for item in _items_for_lens(args.lens):
            disk = item.get("disk_path")
            if not disk:
                continue
            results.append(
                digest_one(
                    Path(disk),
                    lens=str(item.get("lens") or args.lens),
                    skip_chain=args.skip_chain,
                    ocr_backend=args.ocr_backend,
                    ocr_max_pages=ocr_max_pages,
                )
            )

    ok_count = sum(1 for r in results if r.get("ok"))
    doc = {
        "schema": "mkm_paper_digest_run_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "trigger_ko": "소화",
        "ok": ok_count == len(results) and bool(results),
        "success_count": ok_count,
        "total": len(results),
        "results": results,
        "ocr_backend": args.ocr_backend,
        "ocr_max_pages": ocr_max_pages,
        "reproduce": [
            "py scripts/run_mkm_paper_digest_v1.py --lens ijeoma --ocr-backend auto",
            "py scripts/run_mkm_paper_digest_v1.py --pdf data/corpus/.../paper.pdf --lens ijeoma --ocr-backend auto",
            "py scripts/build_haan_lens_coordinate_maps_v1.py",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "success": ok_count, "total": len(results), "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
