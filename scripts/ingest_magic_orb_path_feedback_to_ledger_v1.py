#!/usr/bin/env python3
"""Ingest magic_orb_path_feedback_v1 JSONL into logos_query_path_ledger_v1 (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_query_path_ledger_v1 import (  # noqa: E402
    _query_hash16,
    append_logos_query_path_ledger_line,
    build_entry_from_router,
    resolve_path_index,
)

FEEDBACK_SCHEMA = Path("docs/final/schemas/magic_orb_path_feedback_v1.schema.json")
DEFAULT_FEEDBACK = ROOT / "reports/magic_orb_path_feedback/magic_orb_path_feedback_v1.jsonl"
DEFAULT_ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_CHAIN = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"
DEFAULT_INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
DEFAULT_STATE = ROOT / "reports/logos_path_feedback_ingest_state_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@lru_cache(maxsize=1)
def _feedback_validator():
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema required") from exc
    schema = json.loads((ROOT / FEEDBACK_SCHEMA).read_text(encoding="utf-8-sig"))
    return jsonschema.Draft7Validator(schema)


def validate_feedback_row(row: dict[str, Any]) -> list[str]:
    if not isinstance(row, dict):
        return ["row must be object"]
    errors: list[str] = []
    for err in sorted(_feedback_validator().iter_errors(row), key=lambda e: e.path):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return errors


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": "logos_path_feedback_ingest_state_v1", "processed_event_ids": []}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc.get("processed_event_ids"), list):
        doc["processed_event_ids"] = []
    return doc


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at_utc"] = _utc_now()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def router_matches_feedback(router_doc: dict[str, Any], feedback: dict[str, Any]) -> bool:
    router_hash = _query_hash16(str(router_doc.get("query") or ""))
    return router_hash == str(feedback.get("query_hash") or "")


def ingest_feedback_rows(
    *,
    feedback_rows: list[dict[str, Any]],
    router_doc: dict[str, Any],
    router_path: Path,
    chain_path: Path | None,
    insight_path: Path | None,
    state: dict[str, Any],
    workspace_root: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = workspace_root or ROOT
    processed = set(state.get("processed_event_ids") or [])
    appended: list[str] = []
    skipped: list[dict[str, str]] = []

    for row in feedback_rows:
        event_id = str(row.get("event_id") or "")
        if not event_id:
            skipped.append({"reason": "missing_event_id"})
            continue
        if event_id in processed:
            skipped.append({"event_id": event_id, "reason": "already_processed"})
            continue

        errs = validate_feedback_row(row)
        if errs:
            skipped.append({"event_id": event_id, "reason": "; ".join(errs)})
            continue

        if not router_matches_feedback(router_doc, row):
            skipped.append({"event_id": event_id, "reason": "router_query_hash_mismatch"})
            continue

        path_index = resolve_path_index(
            list(router_doc.get("paths") or []),
            row.get("selected_path_id"),
        )
        entry = build_entry_from_router(
            router_doc,
            query_id=str(row.get("query_id") or ""),
            chain_path=chain_path,
            insight_path=insight_path,
            router_path=router_path,
            vote=str(row.get("vote") or "NONE"),
            selected_path_index=path_index,
        )
        entry["feedback"]["human_annotation"] = f"source_event_id={event_id}"

        if dry_run:
            appended.append(entry["ledger_id"])
            processed.add(event_id)
            continue

        append_logos_query_path_ledger_line(root, entry)
        appended.append(entry["ledger_id"])
        processed.add(event_id)

    state["processed_event_ids"] = sorted(processed)
    return {
        "ok": True,
        "appended_count": len(appended),
        "ledger_ids": appended,
        "skipped": skipped,
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest Magic Orb path feedback into Logos path ledger")
    ap.add_argument("--feedback-jsonl", type=Path, default=DEFAULT_FEEDBACK)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--chain-json", type=Path, default=DEFAULT_CHAIN)
    ap.add_argument("--insight-json", type=Path, default=DEFAULT_INSIGHT)
    ap.add_argument("--state-json", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild-scores", action="store_true")
    args = ap.parse_args(argv)

    feedback_path = args.feedback_jsonl if args.feedback_jsonl.is_absolute() else ROOT / args.feedback_jsonl
    router_path = args.router_json if args.router_json.is_absolute() else ROOT / args.router_json
    chain_path = args.chain_json if args.chain_json.is_absolute() else ROOT / args.chain_json
    insight_path = args.insight_json if args.insight_json.is_absolute() else ROOT / args.insight_json
    state_path = args.state_json if args.state_json.is_absolute() else ROOT / args.state_json

    if not router_path.is_file():
        print(json.dumps({"ok": False, "error": "router_json_missing", "path": str(router_path)}))
        return 1

    feedback_rows = read_jsonl(feedback_path)
    router_doc = json.loads(router_path.read_text(encoding="utf-8-sig"))
    state = load_state(state_path)

    result = ingest_feedback_rows(
        feedback_rows=feedback_rows,
        router_doc=router_doc,
        router_path=router_path,
        chain_path=chain_path if chain_path.is_file() else None,
        insight_path=insight_path if insight_path.is_file() else None,
        state=state,
        workspace_root=ROOT,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        save_state(state_path, state)

    if args.rebuild_scores and not args.dry_run and result["appended_count"] > 0:
        import subprocess

        rc = subprocess.call(
            [sys.executable, str(ROOT / "scripts/build_logos_path_contribution_scores_v1.py")],
            cwd=str(ROOT),
        )
        result["contribution_scores_exit_code"] = rc

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
