#!/usr/bin/env python3
"""Build NotebookLM post-it metadata index from manifest.

Outputs:
- docs/final/artifacts/notebooklm_postit_index_latest.json
- docs/final/artifacts/notebooklm_postit_index_latest.md
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


NOTEBOOK_URL_RE = re.compile(
    r"https://notebooklm\.google\.com/notebook/([a-zA-Z0-9-]+)"
)
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
LIST_TITLE_ID_RE = re.compile(r"-\s*`([^`]+)`\s*\(`([0-9a-fA-F-]{36})`\)")
TITLE_HINT_RE = re.compile(r"제목:\s*\*\*([^*]+)\*\*")


@dataclass
class NotebookPostIt:
    notebook_id: str
    notebook_url: str
    title: str
    track: str = "unknown"
    lane: str = "common"
    status: str = "cataloged"
    evidence_level: str = "B"
    source_of_truth: str = "manifest"
    topic_tags: List[str] = field(default_factory=list)
    summary_1line: str = ""
    context_section: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "notebook_id": self.notebook_id,
            "notebook_url": self.notebook_url,
            "title": self.title,
            "track": self.track,
            "lane": self.lane,
            "status": self.status,
            "evidence_level": self.evidence_level,
            "source_of_truth": self.source_of_truth,
            "topic_tags": self.topic_tags,
            "summary_1line": self.summary_1line,
            "context_section": self.context_section,
        }


def infer_track(section: str, line: str) -> str:
    text = f"{section} {line}".lower()
    if "a 궤적" in text or "fact-lock" in text:
        return "A"
    if "b 궤적" in text or "creative-lock" in text:
        return "B"
    return "unknown"


def infer_lane(text: str) -> str:
    lowered = text.lower()
    if "logos" in lowered or "성경" in text:
        return "logos"
    if "명리" in text or "만세력" in text or "saju" in lowered:
        return "myeongni"
    if "사상" in text or "sasang" in lowered:
        return "sasang"
    return "common"


def infer_tags(text: str) -> List[str]:
    lowered = text.lower()
    tags: List[str] = ["notebooklm", "postit-index"]
    if "ops" in lowered or "작전" in text:
        tags.append("ops")
    if "compression" in lowered or "압축" in text:
        tags.append("compression")
    if "prophecy" in lowered or "예언" in text:
        tags.append("prophecy")
    if "dss" in lowered:
        tags.append("dss")
    if "fusion" in lowered:
        tags.append("fusion")
    if "fact" in lowered:
        tags.append("fact-lock")
    if "research" in lowered or "연구" in text:
        tags.append("research")
    return sorted(set(tags))


def clean_text(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip(" -|")
    return text


def infer_title(line: str, idx: int, lines: List[str]) -> str:
    stripped = line.strip()

    list_match = LIST_TITLE_ID_RE.search(stripped)
    if list_match:
        return clean_text(list_match.group(1))

    hint_match = TITLE_HINT_RE.search(stripped)
    if hint_match:
        return clean_text(hint_match.group(1))

    if "|" in stripped:
        cells = [clean_text(c) for c in stripped.strip("|").split("|")]
        if cells and cells[0] and cells[0].lower() not in {"url", "**url**"}:
            return cells[0]
        # Pull title from a nearby "제목" row if URL row is generic.
        for back in range(1, 8):
            j = idx - back
            if j < 0:
                break
            prev = lines[j].strip()
            if "제목" in prev and "|" in prev:
                prev_cells = [clean_text(c) for c in prev.strip("|").split("|")]
                if len(prev_cells) > 1 and prev_cells[1]:
                    return prev_cells[1]

    return clean_text(stripped)


def read_manifest_entries(manifest_path: Path) -> List[NotebookPostIt]:
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    entries: Dict[str, NotebookPostIt] = {}
    current_section = "root"

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            continue
        if stripped.startswith("### "):
            current_section = stripped[4:].strip()
            continue

        for match in NOTEBOOK_URL_RE.finditer(line):
            notebook_id = match.group(1)
            url = match.group(0)

            # Derive a nearby title candidate.
            title_candidate = infer_title(line, i, lines)
            if not title_candidate or title_candidate.startswith("http"):
                for back in range(1, 4):
                    if i - back >= 0 and lines[i - back].strip():
                        title_candidate = clean_text(lines[i - back])
                        break

            track = infer_track(current_section, line)
            lane = infer_lane(f"{current_section} {line} {title_candidate}")
            tags = infer_tags(f"{current_section} {line} {title_candidate}")
            summary = f"{title_candidate} ({current_section})"

            existing = entries.get(notebook_id)
            if existing is None:
                entries[notebook_id] = NotebookPostIt(
                    notebook_id=notebook_id,
                    notebook_url=url,
                    title=title_candidate,
                    track=track,
                    lane=lane,
                    topic_tags=tags,
                    summary_1line=summary,
                    context_section=current_section,
                )
            else:
                # Keep first title; enrich tags/context.
                existing.topic_tags = sorted(set(existing.topic_tags + tags))
                if existing.track == "unknown" and track != "unknown":
                    existing.track = track
                if existing.lane == "common" and lane != "common":
                    existing.lane = lane

    # Include bare UUID mentions if URL is absent.
    full_text = "\n".join(lines)
    for uid in set(UUID_RE.findall(full_text)):
        if uid not in entries:
            entries[uid] = NotebookPostIt(
                notebook_id=uid,
                notebook_url=f"https://notebooklm.google.com/notebook/{uid}",
                title=f"Notebook {uid[:8]}",
                track="unknown",
                lane="common",
                topic_tags=["notebooklm", "id-only", "postit-index"],
                summary_1line="ID referenced in manifest without direct URL context",
                context_section="id-scan",
            )

    return sorted(entries.values(), key=lambda x: (x.track, x.title.lower()))


def merge_live_notebooks(
    entries: List[NotebookPostIt], live_json_path: Optional[Path]
) -> List[NotebookPostIt]:
    if not live_json_path:
        return entries
    if not live_json_path.exists():
        return entries

    payload = json.loads(live_json_path.read_text(encoding="utf-8"))
    notebooks = payload.get("notebooks", [])
    by_id = {e.notebook_id: e for e in entries}
    by_url = {e.notebook_url: e for e in entries}

    for nb in notebooks:
        nb_id = nb.get("id", "").strip()
        nb_url = nb.get("url", "").strip()
        nb_name = nb.get("name", "").strip() or nb_id
        matched = by_id.get(nb_id) or by_url.get(nb_url)
        if matched:
            matched.status = "live_verified"
            matched.source_of_truth = "manifest+live"
            if matched.title.startswith("Notebook "):
                matched.title = nb_name
            matched.topic_tags = sorted(
                set(matched.topic_tags + ["live-verified"] + nb.get("tags", []))
            )
        else:
            entries.append(
                NotebookPostIt(
                    notebook_id=nb_id,
                    notebook_url=nb_url,
                    title=nb_name,
                    track="unknown",
                    lane=infer_lane(nb_name),
                    status="live_only",
                    evidence_level="A",
                    source_of_truth="live",
                    topic_tags=sorted(
                        set(["notebooklm", "live-only", "postit-index"] + nb.get("tags", []))
                    ),
                    summary_1line=nb.get("description", "Live notebook captured from MCP"),
                    context_section="mcp-list-notebooks",
                )
            )
    return sorted(entries, key=lambda x: (x.track, x.title.lower()))


def write_outputs(entries: List[NotebookPostIt], json_out: Path, md_out: Path) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema": "notebooklm_postit_index_v1",
        "generated_at_utc": generated_at,
        "count": len(entries),
        "items": [e.to_dict() for e in entries],
    }
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# NotebookLM Post-it Index (latest)",
        "",
        f"- generated_at_utc: {generated_at}",
        f"- count: {len(entries)}",
        "",
        "| title | notebook_id | track | lane | status | tags |",
        "|------|-------------|-------|------|--------|------|",
    ]
    for e in entries:
        tags = ", ".join(e.topic_tags[:6])
        lines.append(
            f"| {e.title} | `{e.notebook_id}` | {e.track} | {e.lane} | {e.status} | {tags} |"
        )
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NotebookLM post-it metadata index.")
    parser.add_argument(
        "--manifest",
        default="docs/NotebookLM_sources_manifest.md",
        help="NotebookLM manifest markdown path",
    )
    parser.add_argument(
        "--live-notebooks-json",
        default=None,
        help="Optional MCP list_notebooks output JSON path",
    )
    parser.add_argument(
        "--json-out",
        default="docs/final/artifacts/notebooklm_postit_index_latest.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--md-out",
        default="docs/final/artifacts/notebooklm_postit_index_latest.md",
        help="Output markdown path",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    entries = read_manifest_entries(manifest_path)
    live_path = Path(args.live_notebooks_json) if args.live_notebooks_json else None
    entries = merge_live_notebooks(entries, live_path)
    write_outputs(entries, Path(args.json_out), Path(args.md_out))
    print(f"[ok] notebook post-it index generated: {args.json_out}")
    print(f"[ok] notebook post-it index markdown: {args.md_out}")
    print(f"[ok] entries: {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
