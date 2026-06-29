#!/usr/bin/env python3
"""Pull NotebookLM source via nlm CLI → page images + NL proxy MD (B-track, HOLD)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs/research/raw"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_nlm(args: list[str]) -> tuple[int, str]:
    cmd = ["nlm", *args]
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or p.stderr or "").strip()
    return p.returncode, out


def parse_image_urls(content: str) -> list[str]:
    return re.findall(r"https://lh3\.googleusercontent\.com/notebooklm/[^\s\n]+", content)


def download_images(urls: list[str], dest_dir: Path) -> list[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for i, url in enumerate(urls, 1):
        out = dest_dir / f"page_{i:02d}.jpg"
        if out.is_file() and out.stat().st_size > 1000:
            saved.append(str(out.relative_to(ROOT)).replace("\\", "/"))
            continue
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MKM)"})
        data = urllib.request.urlopen(req, timeout=60).read()
        if len(data) < 500:
            continue
        out.write_bytes(data)
        saved.append(str(out.relative_to(ROOT)).replace("\\", "/"))
    return saved


def write_proxy_md(
    slug: str,
    meta: dict,
    query_doc: dict | None,
    image_paths: list[str],
    raw_content: str = "",
) -> Path:
    answer = ""
    if query_doc:
        answer = (query_doc.get("value") or {}).get("answer") or ""
    lines = [
        f"# NL Proxy — {slug}",
        "",
        f"**generated:** {_utc()[:10]} · `research_only` · `send_gate: HOLD`",
        f"**notebook:** `{meta.get('notebook_id', '')}`",
        f"**source_id:** `{meta.get('source_id', '')}`",
        f"**source_title:** {meta.get('title', '')}",
        f"**source_type:** {meta.get('source_type', '')}",
        "",
        "## Provenance",
        "",
        "- Pulled via `nlm source get` + optional `nlm query notebook --source-ids`",
        "- `physical_verified: false` · `canon_claim: false`",
        "",
    ]
    if raw_content.strip():
        lines.extend(["## Raw source content (nlm source get)", "", raw_content.strip(), ""])
    if answer:
        lines.extend(["## NL extraction (single-source query)", "", answer, ""])
    if image_paths:
        lines.extend(["## Page images", ""])
        for p in image_paths:
            lines.append(f"- `{p}`")
    out = RAW / f"{slug}_nl_proxy.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook-id", required=True)
    ap.add_argument("--source-id", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--query", default="", help="Optional NL query for single-source extract")
    ap.add_argument("--skip-query", action="store_true")
    args = ap.parse_args()

    code, get_out = run_nlm(["source", "get", args.source_id, "--json"])
    if code != 0:
        print(json.dumps({"ok": False, "step": "source_get", "tail": get_out[-400:]}, ensure_ascii=False))
        return code or 1
    get_doc = json.loads(get_out)
    val = get_doc.get("value") or {}
    title = val.get("title") or args.slug
    content = val.get("content") or ""
    source_type = val.get("source_type") or val.get("type") or ""

    urls = parse_image_urls(content)
    img_dir = RAW / f"{args.slug}_nl_pages"
    image_paths = download_images(urls, img_dir) if urls else []

    # Text sources: save raw body alongside proxy
    raw_path = None
    if content.strip() and not urls:
        raw_path = RAW / f"{args.slug}_nl_raw.txt"
        raw_path.write_text(content, encoding="utf-8")
    elif content.strip() and urls:
        # PDF-as-images: keep URL manifest
        (RAW / f"{args.slug}_nl_image_manifest.txt").write_text(content, encoding="utf-8")

    query_doc = None
    if not args.skip_query:
        q = args.query or (
            "이 소스만 사용: (1) 서지 (2) 闡幽抄·格致藁·東武遺稿·知風兆 언급 분류 "
            "(3) 명선록·격치고 직접 인용 한문 구절 (4) 천유초 전문 수록 yes/no"
        )
        code2, q_out = run_nlm(
            [
                "query",
                "notebook",
                args.notebook_id,
                q,
                "--source-ids",
                args.source_id,
                "--json",
            ]
        )
        if code2 == 0:
            query_doc = json.loads(q_out)
            (RAW / f"{args.slug}_nl_query_v1.json").write_text(
                json.dumps(query_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

    meta = {
        "notebook_id": args.notebook_id,
        "source_id": args.source_id,
        "title": title,
        "source_type": source_type,
    }
    proxy = write_proxy_md(args.slug, meta, query_doc, image_paths, raw_content=content if not urls else "")

    log = {
        "schema": "pull_notebooklm_source_to_workspace_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "slug": args.slug,
        "title": title,
        "source_type": source_type,
        "content_chars": len(content),
        "page_images": len(image_paths),
        "raw_text": str(raw_path.relative_to(ROOT)).replace("\\", "/") if raw_path else None,
        "proxy_md": str(proxy.relative_to(ROOT)).replace("\\", "/"),
        "image_dir": str(img_dir.relative_to(ROOT)).replace("\\", "/"),
        "reproduce": (
            f"py scripts/pull_notebooklm_source_to_workspace_v1.py "
            f"--notebook-id {args.notebook_id} --source-id {args.source_id} --slug {args.slug}"
        ),
    }
    out_json = ROOT / "reports/constitution/btrack_pilot" / f"{args.slug}_nl_pull_v1.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
