#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expand one or more pending rows from theme_backlog_v1.jsonl into theme_NN_*.json (Track B, NON_GATING)."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "docs/research/logos_metaphor_db_v1"
DEFAULT_BACKLOG = DEFAULT_DB / "theme_backlog_v1.jsonl"
DEFAULT_SEED_POOL = DEFAULT_DB / "theme_backlog_seed_pool_v1.jsonl"
DEFAULT_SEED_POOL_APPEND = DEFAULT_DB / "theme_backlog_seed_pool_v1_append.jsonl"
THEME_FILE_RE = re.compile(r"^theme_(\d+)_")
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/mkm_logos_research_thin_slice_v0.2.1.schema.json"
BUILD_CARD = ROOT / "scripts/build_logos_research_card_v1.py"
LOG_PATH = ROOT / "reports/logos_theme_expand_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _append_log(row: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _theme_path(db_dir: Path, theme_num: int, slug: str) -> Path:
    return db_dir / f"theme_{theme_num:02d}_{slug}.json"


def _existing_slugs(db_dir: Path) -> set[str]:
    slugs: set[str] = set()
    for path in db_dir.glob("theme_*.json"):
        m = re.match(r"^theme_\d+_(.+)\.json$", path.name)
        if m:
            slugs.add(m.group(1))
    return slugs


def _slug_exists(db_dir: Path, slug: str, known: set[str] | None = None) -> bool:
    if not slug:
        return False
    return slug in (known if known is not None else _existing_slugs(db_dir))


def count_pending_backlog(path: Path) -> int:
    n = 0
    for row in _read_backlog(path):
        status = str(row.get("status", "pending")).lower()
        if status in ("pending", ""):
            n += 1
    return n


def _read_backlog(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def _write_backlog(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _max_theme_num(backlog_rows: list[dict[str, Any]], db_dir: Path) -> int:
    max_n = 0
    for row in backlog_rows:
        try:
            max_n = max(max_n, int(row.get("theme_num", 0)))
        except (TypeError, ValueError):
            continue
    for path in db_dir.glob("theme_*.json"):
        m = THEME_FILE_RE.match(path.name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n


def _theme_file_for_seed(db_dir: Path, row: dict[str, Any]) -> Path | None:
    slug = str(row.get("slug") or "")
    if not slug:
        return None
    try:
        theme_num = int(row["theme_num"])
    except (TypeError, ValueError, KeyError):
        return None
    return _theme_path(db_dir, theme_num, slug)


def _sync_seed_pool_status(seed_rows: list[dict[str, Any]], db_dir: Path) -> None:
    """Mark seeds done when theme JSON exists; reopen queued rows when file is missing."""
    slugs_on_disk = _existing_slugs(db_dir)
    for row in seed_rows:
        slug = str(row.get("slug") or "")
        if slug and slug in slugs_on_disk:
            row["status"] = "done"
            continue
        path = _theme_file_for_seed(db_dir, row)
        if path is not None and path.is_file():
            row["status"] = "done"
            continue
        status = str(row.get("status", "pending")).lower()
        if status == "done":
            continue
        if status == "queued_to_backlog":
            row["status"] = "pending"


def _available_seed_rows(seed_rows: list[dict[str, Any]], db_dir: Path) -> list[dict[str, Any]]:
    _sync_seed_pool_status(seed_rows, db_dir)
    return [
        r
        for r in seed_rows
        if str(r.get("status", "pending")).lower() in ("pending", "")
    ]


def refill_backlog_from_seed(
    backlog_path: Path,
    seed_path: Path,
    db_dir: Path,
    batch: int = 5,
) -> int:
    """Append up to `batch` pending seed rows to backlog when backlog has no pending rows."""
    if count_pending_backlog(backlog_path) > 0:
        return 0
    seed_paths = [seed_path]
    append_path = DEFAULT_SEED_POOL_APPEND
    if seed_path.resolve() != append_path.resolve() and append_path.is_file():
        seed_paths.append(append_path)
    if not any(p.is_file() for p in seed_paths):
        return 0
    backlog_rows = _read_backlog(backlog_path)
    seed_rows: list[dict[str, Any]] = []
    for path in seed_paths:
        if path.is_file():
            seed_rows.extend(_read_backlog(path))
    pending_seed = _available_seed_rows(seed_rows, db_dir)
    if not pending_seed:
        return 0
    slugs_on_disk = _existing_slugs(db_dir)
    next_num = _max_theme_num(backlog_rows, db_dir) + 1
    added = 0
    for seed in pending_seed[:batch]:
        slug = str(seed.get("slug") or "")
        if slug and slug in slugs_on_disk:
            seed["status"] = "done"
            continue
        entry = dict(seed)
        if not entry.get("theme_num"):
            entry["theme_num"] = next_num
            next_num += 1
        else:
            next_num = max(next_num, int(entry["theme_num"]) + 1)
        entry["status"] = "pending"
        slug = str(entry["slug"])
        theme_num = int(entry["theme_num"])
        entry.setdefault(
            "output_path",
            f"docs/research/logos_metaphor_db_v1/theme_{theme_num}_{slug}.json",
        )
        backlog_rows.append(entry)
        seed["status"] = "queued_to_backlog"
        added += 1
    if added:
        _write_backlog(backlog_path, backlog_rows)
        for path in seed_paths:
            if not path.is_file():
                continue
            file_rows = _read_backlog(path)
            _sync_seed_pool_status(file_rows, db_dir)
            _write_backlog(path, file_rows)
        print(f"refilled backlog: +{added} from seed pool", flush=True)
    return added


def _slugify_anchor_id(anchor_node_id: str) -> str:
    return str(anchor_node_id).upper().replace("-", "_")


def _build_from_backlog(entry: dict[str, Any]) -> dict[str, Any]:
    anchor_id = _slugify_anchor_id(str(entry["anchor_node_id"]))
    nodes_in = entry.get("semantic_nodes") or []
    if len(nodes_in) < 1:
        raise ValueError("backlog entry needs at least one semantic_nodes item")
    semantic_nodes: list[dict[str, Any]] = []
    for i, n in enumerate(nodes_in[:6]):
        node_id = str(n.get("node_id") or f"NODE_{anchor_id.replace('ANCHOR_', '')}_{i+1:02d}")
        if not node_id.startswith("NODE_"):
            node_id = "NODE_" + node_id
        domain = str(n.get("research_metaphor_domain") or f"research_metaphor_{entry['slug']}")
        if not domain.startswith("research_metaphor_"):
            domain = "research_metaphor_" + domain
        semantic_nodes.append(
            {
                "node_id": node_id,
                "ref": str(n["ref"]),
                "text": str(n["text"]),
                "edge_type": str(n.get("edge_type") or "is_linked_to"),
                "target_node": anchor_id,
                "impact_weight": float(n.get("impact_weight", 0.8)),
                "research_metaphor_logic_connection": str(
                    n.get("research_metaphor_logic_connection")
                    or f"{entry['slug']} backlog link — ops metaphor only"
                ),
                "research_metaphor_domain": domain,
            }
        )
    gov = entry.get("governance_mapping") or {}
    gov_out = {str(k): str(v) for k, v in gov.items()}
    if "research_metaphor_non_gating_rule" not in gov_out:
        gov_out["research_metaphor_non_gating_rule"] = f"{entry['slug']}_no_track_a_gating"
    return {
        "schema": "mkm_logos_research_thin_slice_v0.2.1",
        "meta": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "weight_source": "commander_assigned_v1",
            "ops_analogy_note": str(entry.get("ops_analogy_note") or entry.get("ops_note") or ""),
        },
        "golden_anchor": {
            "node_id": anchor_id,
            "theme": str(entry["theme"]),
            "ref": str(entry["anchor_ref"]),
            "text": str(entry["anchor_text"]),
        },
        "semantic_nodes": semantic_nodes,
        "governance_mapping": gov_out,
        "commander_insight": str(
            entry.get("commander_insight") or f"{entry['theme']} — Track B backlog expand (NON_GATING)."
        ),
    }


def _validate_doc(doc: dict[str, Any], schema_path: Path) -> None:
    jsonschema = __import__("jsonschema")
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    jsonschema.Draft7Validator(schema).validate(doc)


def _try_gemini(entry: dict[str, Any], schema_path: Path, model: str) -> dict[str, Any] | None:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None
    try:
        from google import genai
    except ImportError:
        return None
    example = (DEFAULT_DB / "theme_01_blood_and_water.json").read_text(encoding="utf-8-sig")[:2500]
    prompt = (
        "Return ONLY one JSON object (no markdown) matching mkm_logos_research_thin_slice_v0.2.1.\n"
        "Required: schema, meta (evidence_tier hypo_research_only, gating_status NON_GATING), "
        "golden_anchor, semantic_nodes (>=3), governance_mapping, commander_insight.\n"
        "All research_metaphor_domain values must start with research_metaphor_.\n"
        "target_node must equal golden_anchor node_id.\n"
        f"Theme brief: {json.dumps(entry, ensure_ascii=False)}\n"
        f"Example shape:\n{example}\n"
    )
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(model=model, contents=prompt)
    text = (resp.text or "").strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    doc = json.loads(m.group(0))
    _validate_doc(doc, schema_path)
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description="Expand Logos theme backlog (Track B)")
    ap.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    ap.add_argument("--db-dir", type=Path, default=DEFAULT_DB)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--max-per-run", type=int, default=1)
    ap.add_argument("--use-gemini", action="store_true", help="Try Gemini when API key set")
    ap.add_argument("--gemini-model", default="gemini-2.5-flash")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--print-pending",
        action="store_true",
        help="Print pending backlog row count to stdout and exit 0",
    )
    ap.add_argument(
        "--auto-refill-seed",
        action="store_true",
        help="When backlog pending=0, append rows from theme_backlog_seed_pool_v1.jsonl",
    )
    ap.add_argument("--seed-pool", type=Path, default=DEFAULT_SEED_POOL)
    ap.add_argument("--seed-refill-batch", type=int, default=5)
    args = ap.parse_args()

    if args.print_pending:
        print(count_pending_backlog(args.backlog))
        return 0

    stop = args.db_dir / "LOGOS_THEME_RUN.stop"
    if stop.is_file():
        print(f"STOP file present: {stop}", flush=True)
        return 0

    if args.auto_refill_seed:
        refill_backlog_from_seed(
            args.backlog, args.seed_pool, args.db_dir, batch=max(1, args.seed_refill_batch)
        )

    rows = _read_backlog(args.backlog)
    if not rows:
        print(f"No backlog at {args.backlog}", flush=True)
        return 0

    slugs_on_disk = _existing_slugs(args.db_dir)
    expanded = 0
    for row in rows:
        if expanded >= args.max_per_run:
            break
        status = str(row.get("status", "pending")).lower()
        if status not in ("pending", ""):
            continue
        theme_num = int(row["theme_num"])
        slug = str(row["slug"])
        if _slug_exists(args.db_dir, slug, slugs_on_disk):
            row["status"] = "done_slug_exists"
            continue
        out_path = _theme_path(args.db_dir, theme_num, slug)
        if out_path.is_file():
            row["status"] = "done_exists"
            slugs_on_disk.add(slug)
            continue

        if args.dry_run:
            print(f"dry_run would write {out_path}", flush=True)
            row["status"] = "dry_run"
            expanded += 1
            continue

        doc: dict[str, Any] | None = None
        mode = "template"
        if args.use_gemini:
            try:
                doc = _try_gemini(row, args.schema, args.gemini_model)
                if doc:
                    mode = "gemini"
            except Exception as exc:  # noqa: BLE001 — log and fall back
                print(f"gemini failed: {exc}", flush=True)
        if doc is None:
            doc = _build_from_backlog(row)
            mode = "template"

        _validate_doc(doc, args.schema)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rc = subprocess.run(
            [sys.executable, str(BUILD_CARD), "--validate-only", "--theme-json", str(out_path)],
            cwd=ROOT,
        ).returncode
        if rc != 0:
            out_path.unlink(missing_ok=True)
            row["status"] = "failed_validate"
            _append_log(
                {
                    "timestamp_utc": _utc_now(),
                    "theme_num": theme_num,
                    "slug": slug,
                    "decision": "failed_validate",
                    "mode": mode,
                }
            )
            return rc

        row["status"] = "done"
        slugs_on_disk.add(slug)
        try:
            row["output_path"] = str(out_path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            row["output_path"] = str(out_path)
        row["expand_mode"] = mode
        expanded += 1
        _append_log(
            {
                "timestamp_utc": _utc_now(),
                "theme_num": theme_num,
                "slug": slug,
                "decision": "expanded",
                "mode": mode,
                "path": str(out_path),
            }
        )
        print(f"OK {out_path} mode={mode}", flush=True)

    _write_backlog(args.backlog, rows)
    if expanded == 0:
        print("No pending backlog rows expanded", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
