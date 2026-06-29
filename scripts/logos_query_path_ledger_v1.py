#!/usr/bin/env python3
"""Logos query path ledger v1 — validate, append, build from router sidecar (B-track).

Schema: docs/final/schemas/logos_query_path_ledger_v1.schema.json
EvoRAG unit: reasoning path (path_id + ordered steps), not flat verse/bridge bags alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

LEDGER_PREFIX = "logos_query_path_ledger_v1"
SCHEMA_REL = Path("docs/final/schemas/logos_query_path_ledger_v1.schema.json")
SAMPLE_REL = Path("reports/logos_query_path_ledger_v1.sample.jsonl")
LATEST_REL = Path("reports/logos_query_path_ledger_v1_latest.jsonl")
VERSE_STEP_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*\.\d+\.\d+$")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _query_hash16(query: str) -> str:
    norm = " ".join(query.strip().split())[:800]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _redact_query(query: str, *, max_len: int = 120) -> str:
    q = " ".join(query.strip().split())
    if len(q) <= max_len:
        return q
    return f"{q[: max_len - 1]}…"


def _rel_path(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


@lru_cache(maxsize=1)
def _schema_validator():
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema required for logos_query_path_ledger validation") from exc
    root = _workspace_root()
    schema = json.loads((root / SCHEMA_REL).read_text(encoding="utf-8-sig"))
    return jsonschema.Draft7Validator(schema)


def validate_logos_query_path_ledger_record(record: dict[str, Any]) -> list[str]:
    if not isinstance(record, dict):
        return ["record must be a JSON object"]
    validator = _schema_validator()
    errors: list[str] = []
    for err in sorted(validator.iter_errors(record), key=lambda e: e.path):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return errors


def _pick_selected_path(paths: list[dict[str, Any]], *, index: int = 0) -> dict[str, Any] | None:
    if not paths:
        return None
    ranked = sorted(
        paths,
        key=lambda p: (
            float(p.get("rank_score") or 0),
            float(p.get("match_score") or 0),
        ),
        reverse=True,
    )
    if index < 0 or index >= len(ranked):
        return ranked[0]
    return ranked[index]


def resolve_path_index(paths: list[dict[str, Any]], path_id: str | None) -> int:
    """Return index in rank-sorted paths for path_id, else 0 (top ranked)."""
    if not path_id or not paths:
        return 0
    ranked = sorted(
        paths,
        key=lambda p: (
            float(p.get("rank_score") or 0),
            float(p.get("match_score") or 0),
        ),
        reverse=True,
    )
    for i, path in enumerate(ranked):
        if str(path.get("path_id") or "") == path_id:
            return i
    for i, path in enumerate(paths):
        if str(path.get("path_id") or "") == path_id:
            return i
    return 0


def _steps_to_derived(steps: list[str]) -> tuple[list[str], list[str]]:
    bridges: list[str] = []
    verses: list[str] = []
    for step in steps:
        s = str(step).strip()
        if not s:
            continue
        if VERSE_STEP_RE.match(s):
            verses.append(s)
        else:
            bridges.append(s)
    return bridges, verses


def build_entry_from_router(
    router_doc: dict[str, Any],
    *,
    query_id: str = "",
    chain_path: Path | None = None,
    insight_path: Path | None = None,
    router_path: Path | None = None,
    vote: str = "NONE",
    selected_path_index: int = 0,
    latency_ms: int | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    query = str(router_doc.get("query") or "").strip()
    if not query:
        raise ValueError("router_doc.query missing")

    paths = list(router_doc.get("paths") or [])
    selected = _pick_selected_path(paths, index=selected_path_index)
    if not selected:
        raise ValueError("router_doc.paths empty — cannot build path ledger entry")

    steps = [str(s) for s in (selected.get("steps") or []) if str(s).strip()]
    if not steps:
        raise ValueError("selected path has no steps")

    bridge_ids, verse_ids = _steps_to_derived(steps)
    qh = _query_hash16(query)
    ts = _utc_now()
    ledger_id = f"q_{qh}_{int(datetime.now(timezone.utc).timestamp())}"
    root = _workspace_root()

    rank_score = selected.get("rank_score")
    if rank_score is not None:
        rank_score = float(rank_score)

    entry: dict[str, Any] = {
        "schema": "logos_query_path_ledger_v1",
        "version": "1.0.0",
        "ledger_id": ledger_id,
        "ts_utc": ts,
        "query_hash": qh,
        "query_redacted": _redact_query(query),
        "governance": {
            "research_only": True,
            "non_gating": True,
            "send_gate": "HOLD",
            "hypothesis_tier": "B",
        },
        "provenance": {
            "router_sidecar": _rel_path(root, router_path) or "reports/question_logos_subgraph_router_sidecar_v1_latest.json",
        },
        "retrieval": {
            "selected_path_id": str(selected.get("path_id") or "unknown_path"),
            "selected_steps": steps,
            "candidate_path_ids": [
                str(p.get("path_id"))
                for p in paths
                if p.get("path_id") is not None
            ][:32],
            "rank_score": rank_score,
            "bridge_ids": bridge_ids[:32],
            "verse_ids": verse_ids[:32],
            "path_score_baseline": 100.0,
        },
        "feedback": {
            "vote": vote if vote in {"UP", "DOWN", "NONE"} else "NONE",
            "scope": "selected_path" if vote in {"UP", "DOWN"} else "none",
            "is_flagged": False,
            "human_annotation": "",
        },
    }

    if query_id:
        entry["query_id"] = query_id
    if insight_path:
        entry["provenance"]["insight_artifact"] = _rel_path(root, insight_path)
    if chain_path:
        entry["provenance"]["chain_artifact"] = _rel_path(root, chain_path)

    runtime: dict[str, Any] = {}
    if latency_ms is not None:
        runtime["latency_ms"] = int(latency_ms)
    rv = router_doc.get("version")
    if rv:
        runtime["router_version"] = str(rv)
    if model_version:
        runtime["model_version"] = model_version
    if runtime:
        entry["runtime"] = runtime

    return entry


def append_logos_query_path_ledger_line(
    workspace_root: Path,
    record: dict[str, Any],
    *,
    mirror_latest: bool = True,
) -> Path:
    errs = validate_logos_query_path_ledger_record(record)
    if errs:
        raise ValueError("; ".join(errs))

    out_dir = workspace_root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    daily = out_dir / f"{LEDGER_PREFIX}_{now.strftime('%Y%m%d')}.jsonl"
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with daily.open("a", encoding="utf-8") as f:
        f.write(line)
    if mirror_latest:
        latest = workspace_root / LATEST_REL
        with latest.open("a", encoding="utf-8") as f:
            f.write(line)
    return daily


def validate_jsonl_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        errs = validate_logos_query_path_ledger_record(obj)
        if errs:
            raise ValueError(f"line {i}: {'; '.join(errs)}")
        n += 1
    return n


def iter_ledger_records(
    workspace_root: Path,
    *,
    glob_pattern: str = f"{LEDGER_PREFIX}*.jsonl",
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    base = workspace_root / "reports"
    if not base.is_dir():
        return []
    for path in sorted(base.glob(glob_pattern)):
        if path.name.endswith(".sample.jsonl"):
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            lid = str(record.get("ledger_id") or "")
            if lid:
                by_id[lid] = record
            else:
                by_id[f"__anon_{len(by_id)}"] = record
    return list(by_id.values())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cmd_from_router(args: argparse.Namespace, root: Path) -> int:
    router_path = args.router_json if args.router_json.is_absolute() else root / args.router_json
    if not router_path.is_file():
        print(json.dumps({"ok": False, "error": "router_json_missing", "path": str(router_path)}))
        return 1

    router_doc = _read_json(router_path)
    chain_path = None
    if args.chain_json:
        chain_path = args.chain_json if args.chain_json.is_absolute() else root / args.chain_json
    insight_path = None
    if args.insight_json:
        insight_path = args.insight_json if args.insight_json.is_absolute() else root / args.insight_json

    entry = build_entry_from_router(
        router_doc,
        query_id=args.query_id or "",
        chain_path=chain_path,
        insight_path=insight_path,
        router_path=router_path,
        vote=args.vote,
        selected_path_index=args.selected_path_index,
        latency_ms=args.latency_ms,
        model_version=args.model_version,
    )

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "entry": entry}, ensure_ascii=False))
        return 0

    out_path = append_logos_query_path_ledger_line(root, entry)
    print(
        json.dumps(
            {
                "ok": True,
                "ledger_id": entry["ledger_id"],
                "selected_path_id": entry["retrieval"]["selected_path_id"],
                "out_daily": str(out_path.relative_to(root)).replace("\\", "/"),
                "out_latest": str(LATEST_REL).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Logos query path ledger v1 (B-track · path-centric)")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate JSONL file")
    p_val.add_argument("--path", type=Path, required=True)

    p_val_sample = sub.add_parser("validate-sample", help="Validate bundled sample JSONL")
    p_val_sample.add_argument("--path", type=Path, default=None)

    p_app = sub.add_parser("append", help="Append one JSON object from stdin or --json")
    p_app.add_argument("--json", type=str, default="")

    p_router = sub.add_parser("from-router", help="Build + append entry from router sidecar JSON")
    p_router.add_argument(
        "--router-json",
        type=Path,
        default=Path("reports/question_logos_subgraph_router_sidecar_v1_latest.json"),
    )
    p_router.add_argument("--chain-json", type=Path, default=None)
    p_router.add_argument("--insight-json", type=Path, default=None)
    p_router.add_argument("--query-id", default="")
    p_router.add_argument("--vote", choices=("UP", "DOWN", "NONE"), default="NONE")
    p_router.add_argument("--selected-path-index", type=int, default=0)
    p_router.add_argument("--latency-ms", type=int, default=None)
    p_router.add_argument("--model-version", default=None)
    p_router.add_argument("--dry-run", action="store_true")

    args = p.parse_args(argv)
    root = _workspace_root()

    if args.cmd == "validate":
        n = validate_jsonl_file(args.path)
        print(f"OK: {n} line(s) validated: {args.path}")
        return 0

    if args.cmd == "validate-sample":
        path = args.path or (root / SAMPLE_REL)
        n = validate_jsonl_file(path)
        print(f"OK: {n} line(s) validated: {path}")
        return 0

    if args.cmd == "append":
        raw = args.json.strip() if args.json else sys.stdin.read()
        record = json.loads(raw)
        out = append_logos_query_path_ledger_line(root, record)
        print(f"appended to {out}")
        return 0

    if args.cmd == "from-router":
        return cmd_from_router(args, root)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
