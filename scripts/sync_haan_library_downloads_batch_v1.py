#!/usr/bin/env python3
"""Sync 하안도서관 Downloads batch → corpus + NL proxies + inventory (research_only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOWNLOADS = Path(r"C:\Users\PRO\Downloads")
OUT_INDEX = ROOT / "reports/constitution/btrack_pilot/haan_library_downloads_batch_v1_latest.json"
RAW = ROOT / "docs/research/raw"

LENS_DIRS = {
    "logos": ROOT / "data/corpus/logos/library_capture/2026-06-28",
    "myeongri": ROOT / "data/corpus/myeongri/library_capture/2026-06-28",
    "ijeoma": ROOT / "data/corpus/ijeoma/secondary/library_capture/2026-06-28",
    "ijeoma_logos_bridge": ROOT / "data/corpus/ijeoma/secondary/library_capture/2026-06-28/bridge",
}

LOGOS_RE = re.compile(r"요한계시록|성경|성서|게마트리아|루가|바흐|교회")
MYEONGRI_RE = re.compile(r"명리|사주|타로|육친|오행")
IJEoma_RE = re.compile(
    r"이제마|동무|격치|四象|四像|東武|千|李濟馬|李濟馬|行命|素質|格致|遺藁|東醫"
)
SKIP_RE = re.compile(r"QuBICS|Confirmation_for_Booking|CNTS-00047835836\.rdf|Figma")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _slugify(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r"[^\w\-]+", "_", stem, flags=re.UNICODE)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return (slug or "ITEM")[:72]


def classify(name: str) -> str | None:
    if SKIP_RE.search(name):
        return None
    if not name.lower().endswith((".pdf", ".txt")):
        return None
    if LOGOS_RE.search(name):
        if IJEoma_RE.search(name):
            return "ijeoma_logos_bridge"
        return "logos"
    if MYEONGRI_RE.search(name):
        return "myeongri"
    if IJEoma_RE.search(name):
        return "ijeoma"
    return None


def _lens_tag(lens: str) -> str:
    return {
        "logos": "LENS_LOGOS",
        "myeongri": "LENS_MYEONGNI",
        "ijeoma": "IJEOMA_BTRACK",
        "ijeoma_logos_bridge": "IJEOMA_BTRACK,LENS_LOGOS",
    }.get(lens, "UNKNOWN")


def _write_nl_proxy(
    *,
    slug: str,
    lens: str,
    rel_disk: str,
    sha: str,
    title: str,
    text_body: str | None,
) -> Path:
    proxy_name = f"HAAN_LIBRARY_{lens.upper()}_{slug}_nl_proxy.md"
    out = RAW / proxy_name
    lines = [
        f"# NL Proxy — HAAN_LIBRARY_{slug}",
        "",
        f"**generated:** {_utc()} · `research_only` · `send_gate: HOLD`",
        f"**lens:** {_lens_tag(lens)}",
        f"**source_type:** library_capture_haan_2026-06-28",
        f"**disk_path:** `{rel_disk}`",
        f"**sha256:** `{sha}`",
        "",
        "## Bibliographic",
        "",
        title,
        "",
        "## MKM boundaries",
        "",
        "- 하안도서관 협약 PC 세션 2026-06-28 Downloads → workspace corpus",
        "- `[CANON]`·Track A·실매매·macro gating 승격 없음",
        "- 성경(Logos) = `[NON_GATING]` assistive only",
        "",
    ]
    if text_body and text_body.strip():
        lines.extend(["## Text (ingested)", "", "```", text_body.strip()[:12000], "```", ""])
    else:
        lines.extend(
            [
                "## Text",
                "",
                "Full PDF on disk. Digest: `py scripts/run_mkm_paper_digest_v1.py --pdf "
                f"{rel_disk} --lens {lens}`",
                "",
            ]
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def sync_downloads(downloads: Path, *, dry_run: bool) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for src in sorted(downloads.iterdir()):
        if not src.is_file():
            continue
        lens = classify(src.name)
        if lens is None:
            continue
        dest_dir = LENS_DIRS[lens]
        dest = dest_dir / src.name
        rel_disk = str(dest.relative_to(ROOT)).replace("\\", "/")
        sha = _sha256(src)
        copied = False
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if dest.is_file():
                if _sha256(dest) == sha:
                    copied = False
                else:
                    shutil.copy2(src, dest)
                    copied = True
            else:
                shutil.copy2(src, dest)
                copied = True
        text_body = None
        if src.suffix.lower() == ".txt":
            try:
                text_body = src.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text_body = None
        slug = _slugify(src.name)
        proxy_rel = None
        if not dry_run:
            proxy = _write_nl_proxy(
                slug=slug,
                lens=lens,
                rel_disk=rel_disk,
                sha=sha,
                title=src.stem.replace("_", " "),
                text_body=text_body,
            )
            proxy_rel = str(proxy.relative_to(ROOT)).replace("\\", "/")
        items.append(
            {
                "file": src.name,
                "lens": lens,
                "disk_path": rel_disk,
                "sha256": sha,
                "bytes": src.stat().st_size,
                "copied": copied,
                "nl_proxy": proxy_rel,
            }
        )
    doc = {
        "schema": "haan_library_downloads_batch_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "source_downloads": str(downloads),
        "count": len(items),
        "by_lens": {
            k: sum(1 for i in items if i["lens"] == k) for k in LENS_DIRS
        },
        "items": items,
    }
    if not dry_run:
        OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
        OUT_INDEX.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


PHOTO_PAGE_MAP: dict[str, dict[str, str]] = {
    "IMG_0155.jpeg": {"page": "title", "work": "park1985_geukchigo", "note": "표지 東武格致藁"},
    "IMG_0156.jpeg": {"page": "toc", "work": "park1985_geukchigo", "note": "格致藁目錄 상"},
    "IMG_0157.jpeg": {"page": "toc_cont", "work": "park1985_geukchigo", "note": "목차 하·부록"},
    "IMG_0158.jpeg": {"page": "colophon", "work": "park1985_geukchigo", "note": "판권 1985 태양사"},
    "IMG_0160.jpeg": {"page": "p.383", "work": "park1985_buyugochyo", "note": "附遺藁抄 본문"},
    "IMG_0161.jpeg": {"page": "p.384", "work": "park1985_buyugochyo", "note": "附遺藁抄 본문"},
    "IMG_0162.jpeg": {"page": "p.385", "work": "park1985_buyugochyo", "note": "附遺藁抄 본문"},
    "IMG_0163.jpeg": {"page": "p.386", "work": "park1985_buyugochyo", "note": "附遺藁抄 본문(추정)"},
    "IMG_0164.jpeg": {"page": "p.145", "work": "jangseogak_vol2", "note": "장서각 제2집 이창일 동무유고"},
    "IMG_0165.jpeg": {"page": "p.146", "work": "jangseogak_vol2", "note": "장서각 제2집 천유초 정의"},
    "IMG_0166.jpeg": {"page": "p.146_cont", "work": "jangseogak_vol2", "note": "장서각 제2집 각주"},
}


def write_photo_map() -> Path:
    out = ROOT / "data/corpus/ijeoma/_inventory/cheonyucho_downloads_photo_page_map_v1.json"
    doc = {
        "schema": "cheonyucho_downloads_photo_page_map_v1",
        "generated_at_utc": _utc(),
        "base_dir": "data/corpus/ijeoma/originals/cheonyucho_partial/photos_2026-06-28/downloads",
        "photos": PHOTO_PAGE_MAP,
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--downloads", type=Path, default=DEFAULT_DOWNLOADS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--photo-map-only", action="store_true")
    args = ap.parse_args()

    if args.photo_map_only:
        p = write_photo_map()
        print(json.dumps({"ok": True, "photo_map": str(p)}, ensure_ascii=False))
        return 0

    doc = sync_downloads(args.downloads, dry_run=args.dry_run)
    pmap = write_photo_map()
    print(
        json.dumps(
            {
                "ok": True,
                "count": doc["count"],
                "by_lens": doc["by_lens"],
                "index": str(OUT_INDEX),
                "photo_map": str(pmap),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
