#!/usr/bin/env python3
"""Build workspace-wide post-it metadata index (docs/scripts/reports)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence


DEFAULT_INCLUDE_DIRS = ("docs", "scripts", "reports")
DEFAULT_EXTENSIONS = (".md", ".json", ".jsonl", ".py", ".ps1", ".yml", ".yaml")
SKIP_DIR_FRAGMENTS = (
    ".git/",
    ".cursor/",
    "__pycache__/",
    ".venv/",
    "node_modules/",
)


def should_skip(path: Path) -> bool:
    p = path.as_posix() + ("/" if path.is_dir() else "")
    return any(fragment in p for fragment in SKIP_DIR_FRAGMENTS)


def infer_type(path: Path) -> str:
    p = path.as_posix().lower()
    if "/docs/" in f"/{p}/":
        return "document"
    if "/scripts/" in f"/{p}/":
        return "automation"
    if "/reports/" in f"/{p}/":
        return "artifact"
    return "other"


def infer_track_rel(rel_posix: str) -> str:
    """Heuristic A/B lane from workspace-relative path — not compression engine output."""
    text = rel_posix.lower()

    def has_any(markers: Sequence[str]) -> bool:
        return any(m in text for m in markers)

    # B-track: research, hypothesis, pilot benches (specific before broad)
    if has_any(
        (
            "btrack",
            "btrack_pilot",
            "/research/",
            "hypo",
            "sandbox",
            "trackb_",
            "track_b",
            "/data/logos/btrack",
            "general_prophecy",
            "saving_the_news",
            "aramaic",
            "comp_atom",
            "comp_univ",
            "truthfulqa",
            "lens_music",
            "premium_multilens",
            "prophecy_restoration",
            "prophecy_prior_threshold",
            "/mkm-study",
            "/mkm/mkm-study",
            "trackc_evidence",
            "track_c_ip",
            "logos_metaphor",
            "external_research",
            "/archive/",
        )
    ):
        return "B"

    # A-track: governance, ops, commercialization, trading monorepo
    if has_any(
        (
            "track_a",
            "/track-a",
            "commercial",
            "commercialization",
            "p0_commercial",
            "/ops/",
            "ops_",
            "projects/bitcoin-trading/",
            "ops/windows-rehearsal",
            "ops_phase1",
            "automation_registry",
            "verify_p0",
            "fact_lock",
            "run_fact_lock",
            "multilens_p1_production",
            "dual-regime",
            "amsaeng_eosa",
            "safe_ops",
            "live_trading",
            "constitution_inference",
            "constitution_gates",
            "compression_automation",
            "run_track_a",
        )
    ):
        return "A"

    if text.startswith("docs/final/"):
        return "A"

    if text.startswith("projects/"):
        if has_any(("no1kmedi", "mkm-life", "jema12")):
            return "A"
        return "A"

    if text.startswith("scripts/"):
        if has_any(
            (
                "btrack",
                "hypo",
                "research",
                "prophecy_restoration",
                "general_prophecy",
                "trackc_",
                "lens_music",
                "aramaic",
                "experimental",
                "cinematic",
                "/audio/",
            )
        ):
            return "B"
        if has_any(
            (
                "track_a",
                "p0_",
                "verify_",
                "ops_",
                "amsaeng",
                "fact_lock",
                "compression_",
                "workspace_postit",
            )
        ):
            return "A"
        return "A"

    if text.startswith("reports/"):
        if has_any(
            ("btrack", "constitution/btrack", "prophecy_promotion", "logos_metaphor")
        ):
            return "B"
        return "A"

    if text.startswith("docs/"):
        if text.startswith("docs/api/"):
            return "A"
        return "A"

    return "unknown"


def infer_track(path: Path, *, rel_posix: str | None = None) -> str:
    rel = rel_posix if rel_posix is not None else path.as_posix()
    return infer_track_rel(rel)


def infer_lane(path: Path) -> str:
    text = path.as_posix().lower()
    if "logos" in text:
        return "logos"
    if "myeongni" in text or "manse" in text or "saju" in text:
        return "myeongni"
    if "sasang" in text:
        return "sasang"
    return "common"


def infer_status(path: Path) -> str:
    name = path.name.lower()
    if "latest" in name:
        return "active_latest"
    if "draft" in name:
        return "draft"
    if "archive" in path.as_posix().lower():
        return "archived"
    return "cataloged"


def infer_evidence_level(path: Path) -> str:
    p = path.as_posix().lower()
    if p.endswith(".py") or "constitution" in p or "schema" in p:
        return "A"
    if p.endswith(".json") or p.endswith(".jsonl"):
        return "B"
    return "C"


def infer_tags(path: Path) -> List[str]:
    text = path.as_posix().lower()
    tags = ["workspace-postit"]
    if "/docs/" in f"/{text}/":
        tags.append("docs")
    if "/scripts/" in f"/{text}/":
        tags.append("scripts")
    if "/reports/" in f"/{text}/":
        tags.append("reports")
    if "notebooklm" in text:
        tags.append("notebooklm")
    if "compression" in text:
        tags.append("compression")
    if "prophecy" in text:
        tags.append("prophecy")
    if "gate" in text:
        tags.append("gate")
    if "dashboard" in text:
        tags.append("dashboard")
    if "schema" in text:
        tags.append("schema")
    return sorted(set(tags))


def make_item(root: Path, path: Path) -> Dict[str, object]:
    rel = path.relative_to(root).as_posix()
    return {
        "path": rel,
        "type": infer_type(path),
        "track": infer_track_rel(rel),
        "lane": infer_lane(path),
        "status": infer_status(path),
        "evidence_level": infer_evidence_level(path),
        "source_of_truth": "workspace",
        "topic_tags": infer_tags(path),
        "summary_1line": f"{path.stem} ({path.suffix.lstrip('.')})",
    }


def collect_files(root: Path, include_dirs: Sequence[str], exts: Sequence[str]) -> List[Path]:
    results: List[Path] = []
    ext_set = {e.lower() for e in exts}
    for d in include_dirs:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if should_skip(p):
                continue
            if p.suffix.lower() not in ext_set:
                continue
            results.append(p)
    return sorted(results, key=lambda x: x.as_posix().lower())


def write_outputs(items: List[Dict[str, object]], json_out: Path, md_out: Path) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema": "workspace_postit_index_v1",
        "generated_at_utc": generated_at,
        "count": len(items),
        "items": items,
    }
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Workspace Post-it Index (latest)",
        "",
        f"- generated_at_utc: {generated_at}",
        f"- count: {len(items)}",
        "",
        "| path | type | track | lane | status | evidence |",
        "|------|------|-------|------|--------|----------|",
    ]
    for it in items:
        lines.append(
            f"| `{it['path']}` | {it['type']} | {it['track']} | {it['lane']} | {it['status']} | {it['evidence_level']} |"
        )
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build workspace post-it index.")
    parser.add_argument("--root", default=".", help="Workspace root")
    parser.add_argument(
        "--include-dirs",
        nargs="+",
        default=list(DEFAULT_INCLUDE_DIRS),
        help="Directories to scan",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(DEFAULT_EXTENSIONS),
        help="File extensions to include",
    )
    parser.add_argument(
        "--json-out",
        default="docs/final/artifacts/workspace_postit_index_latest.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--md-out",
        default="docs/final/artifacts/workspace_postit_index_latest.md",
        help="Output markdown path",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = collect_files(root, args.include_dirs, args.extensions)
    items = [make_item(root, p) for p in files]
    write_outputs(items, root / args.json_out, root / args.md_out)
    print(f"[ok] workspace post-it index generated: {args.json_out}")
    print(f"[ok] workspace post-it index markdown: {args.md_out}")
    print(f"[ok] entries: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
