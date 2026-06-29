#!/usr/bin/env python3
"""Export System2 Vertex staging jsonl rows to local Agent Search pack (markdown)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING = ROOT / "reports" / "mkm_system2_vertex_staging_v1.jsonl"
DEFAULT_OUT_DIR = ROOT / "reports" / "agent_search_corpus" / "system2-gate"
DEFAULT_MANIFEST = ROOT / "reports" / "mkm_system2_vertex_staging_export_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_staging_rows(path: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def export_pack(
    staging_path: Path,
    *,
    out_dir: Path,
    limit: int = 50,
) -> dict[str, Any]:
    rows = load_staging_rows(staging_path, limit=limit)
    out_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        stamp = (row.get("recorded_at_utc") or "unknown").replace(":", "-")
        name = f"system2_gate_pass_{i}_{stamp}.md"
        out_path = out_dir / name
        text = row.get("text") or ""
        body = (
            f"# System2 gate verified row\n\n"
            f"Source tag: `{row.get('source_tag')}`\n\n"
            f"Recorded: `{row.get('recorded_at_utc')}`\n\n"
            f"Human sign-off required: `{row.get('human_sign_off_required')}`\n\n"
            f"{text}\n"
        )
        out_path.write_text(body, encoding="utf-8")
        local_ref = (
            out_path.relative_to(ROOT).as_posix()
            if out_path.is_relative_to(ROOT)
            else str(out_path)
        )
        exported.append(
            {
                "ok": True,
                "local_md": local_ref,
                "gcs_object": f"agent-search-docs/system2-gate__{name}",
                "bytes": out_path.stat().st_size,
            }
        )
    manifest = {
        "schema": "mkm_system2_vertex_staging_export_v1",
        "generated_at_utc": _utc(),
        "staging_jsonl": str(staging_path),
        "out_dir": str(out_dir),
        "row_count": len(rows),
        "exported_count": len(exported),
        "files": exported,
        "boundary_ack": "Markdown export only; Vertex import via invoke_system2_vertex_staging_upload_v1.py + human sign-off.",
    }
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--staging-jsonl", default=str(DEFAULT_STAGING))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--manifest-out", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    doc = export_pack(Path(args.staging_jsonl), out_dir=Path(args.out_dir), limit=args.limit)
    out = Path(args.manifest_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["exported_count"] > 0 or doc["row_count"] == 0, "manifest": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
