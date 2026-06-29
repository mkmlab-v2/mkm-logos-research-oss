#!/usr/bin/env python3
"""BigSet AGPL isolation bridge — subprocess/artifact only, no source import.

Tier-0 theology corpus ingest boundary [HYPO] · B-track · send_gate HOLD.

Reproducible (dry-run, CI-safe):
  py scripts/bigset_agent_bridge_v1.py --dry-run

Live (tier_15 BYOK — requires `bigset` CLI + keys outside MKM repo):
  py scripts/bigset_agent_bridge_v1.py --live --rows 10
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURE_CSV = ROOT / "tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv"
SCHEMA_PATH = ROOT / "docs/final/schemas/bigset_theology_tier0_row_v1.schema.json"
DEFAULT_RAW_DIR = ROOT / "docs/research/raw"
DEFAULT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_agent_bridge_v1_latest.json"

REQUIRED_COLUMNS = [
    "source_url",
    "tradition",
    "scholar_school",
    "corpus_tier",
    "verse_ref",
    "excerpt",
    "retrieval_timestamp_utc",
    "conflict_group_id",
    "school_tier",
    "interpretation_ko",
    "citation_lock_anchor",
]

CONFLICT_COLUMNS = [
    "conflict_group_id",
    "school_tier",
    "interpretation_ko",
    "citation_lock_anchor",
]

THEOLOGY_PROMPT_TEMPLATE = (
    "Theological open-web bibliography on Benei HaElohim / sons of God in Genesis 6, "
    "DSS fragments, LXX, and pseudepigrapha (1 Enoch). "
    "Columns (required): source_url, tradition, scholar_school, corpus_tier "
    "(A|B|C|D|unknown), verse_ref, excerpt, retrieval_timestamp_utc (ISO-8601 UTC), "
    "conflict_group_id (e.g. MKM_CONCEPT_SONS_OF_GOD), school_tier "
    "(historical_criticism|judaic_mysticism|...), interpretation_ko, citation_lock_anchor (URL). "
    "Do NOT merge conflicting schools into one row. "
    "Every row must include a real public citation_lock_anchor. "
    "No investment or prophecy claims."
)

NEPHILIM_WATCHER_PROMPT_TEMPLATE = (
    "Theological open-web bibliography on Nephilim, Watchers, and Genesis 6:1-4 "
    "in 1 Enoch, Jubilees, DSS, and Second Temple reception (distinct URLs from Benei HaElohim surveys). "
    "Columns (required): source_url, tradition, scholar_school, corpus_tier "
    "(A|B|C|D|unknown), verse_ref, excerpt, retrieval_timestamp_utc (ISO-8601 UTC), "
    "conflict_group_id (MKM_CONCEPT_NEPHILIM or MKM_CONCEPT_SONS_OF_GOD), school_tier, "
    "interpretation_ko, citation_lock_anchor (URL). "
    "Do NOT merge conflicting schools into one row. "
    "Every row must include a real public citation_lock_anchor. "
    "No investment or prophecy claims."
)

OLLAMA_SCHEMA_HINT = (
    " BigSet schema rule: source_url is the ONLY primary key column "
    "(is_primary_key true on source_url only; retrieval_timestamp_utc and citation_lock_anchor are NOT primary keys). "
    'primary_key array must be ["source_url"].'
)


def _resolve_prompt(base: str, *, live: bool) -> str:
    if not live:
        return base
    try:
        from scripts.bigset_free_tier_profile_v1 import load_dotenv_quiet, resolve_profile

        load_dotenv_quiet()
        if resolve_profile().get("profile_mode") == "ollama_local":
            return base + OLLAMA_SCHEMA_HINT
    except Exception:
        pass
    return base


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _normalize_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    """Backfill Tier-0 fields when BigSet omits optional duplicates (common on :free models)."""
    notes: list[str] = []
    for row in rows:
        if not str(row.get("citation_lock_anchor") or "").strip():
            url = str(row.get("source_url") or "").strip()
            if url:
                row["citation_lock_anchor"] = url
                if "citation_lock_anchor_from_source_url" not in notes:
                    notes.append("citation_lock_anchor_from_source_url")
        if not str(row.get("interpretation_ko") or "").strip():
            excerpt = str(row.get("excerpt") or "").strip()
            if excerpt:
                row["interpretation_ko"] = excerpt[:500]
                if "interpretation_ko_from_excerpt" not in notes:
                    notes.append("interpretation_ko_from_excerpt")
    return rows, notes


def _validate_rows(rows: list[dict[str, str]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for i, row in enumerate(rows):
        for col in REQUIRED_COLUMNS:
            if not str(row.get(col) or "").strip():
                errors.append(f"row {i}: missing {col}")
        url = str(row.get("source_url") or "").strip()
        if url and not urlparse(url).scheme:
            errors.append(f"row {i}: source_url missing scheme")
        tier = str(row.get("corpus_tier") or "").strip()
        if tier and tier not in {"A", "B", "C", "D", "unknown"}:
            errors.append(f"row {i}: invalid corpus_tier={tier}")
        anchor = str(row.get("citation_lock_anchor") or row.get("source_url") or "").strip()
        if anchor and not urlparse(anchor).scheme:
            errors.append(f"row {i}: citation_lock_anchor missing scheme")
    return len(errors) == 0, errors


def _write_csv(rows: list[dict[str, str]], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else REQUIRED_COLUMNS + ["hypothesis_tier", "research_only"]
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _wrap_markdown(csv_path: Path, md_path: Path, *, topic_slug: str, mode: str) -> None:
    rows = _read_csv_rows(csv_path)
    lines = [
        f"# BigSet Tier-0 ingest wrapper — {topic_slug}",
        "",
        f"- generated_at_utc: {_now()}",
        f"- mode: {mode}",
        f"- research_only: true",
        f"- send_gate: HOLD",
        f"- hypothesis_tier: B",
        f"- source_csv: `{csv_path.relative_to(ROOT).as_posix()}`",
        "",
        "## Rows (for digestion chain)",
        "",
    ]
    for i, row in enumerate(rows, 1):
        lines.append(f"### Row {i}")
        for k in REQUIRED_COLUMNS:
            lines.append(f"- **{k}**: {row.get(k, '')}")
        if row.get("send_gate_row"):
            lines.append(f"- **send_gate_row**: {row.get('send_gate_row')}")
        lines.append("")
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _azure_rate_limit_cooldown() -> dict[str, Any]:
    """Buffer before BigSet schema inference on Azure S0 (~1 req / 60s)."""
    try:
        from scripts.bigset_free_tier_profile_v1 import load_dotenv_quiet, resolve_profile

        load_dotenv_quiet()
        profile_mode = resolve_profile().get("profile_mode")
        base_url = (os.environ.get("OPENROUTER_BASE_URL") or "").lower()
        art = ROOT / "docs/final/artifacts/bigset_free_tier_profile_v1_latest.json"
        art_mode = None
        if art.is_file():
            try:
                art_mode = json.loads(art.read_text(encoding="utf-8")).get("applied", {}).get("profile_mode")
            except json.JSONDecodeError:
                art_mode = None
        azure_active = (
            profile_mode == "azure_openai"
            or art_mode == "azure_openai"
            or "openai.azure.com" in base_url
        )
        if not azure_active:
            return {"skipped": True, "reason": "not_azure_profile"}
    except Exception:
        return {"skipped": True, "reason": "profile_resolve_failed"}
    wait_s = int(os.environ.get("MKM_AZURE_OPENAI_COOLDOWN_SEC", "65"))
    if wait_s > 0:
        time.sleep(wait_s)
    return {"waited_sec": wait_s, "reason": "azure_s0_rate_limit_buffer"}


def _run_live_bigset(
    *,
    prompt: str,
    rows: int,
    out_csv: Path,
    timeout_sec: int,
) -> dict[str, Any]:
    exe = shutil.which("bigset")
    if not exe:
        return {"ok": False, "error": "bigset_cli_not_found", "hint": "npm install -g @adamexu/bigset"}
    cmd = [
        exe,
        "create",
        prompt,
        "--rows",
        str(rows),
        "--wait",
        "--csv",
        str(out_csv),
    ]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        csv_ok = out_csv.is_file() and out_csv.stat().st_size > 0
        return {
            "ok": csv_ok,
            "partial_csv": csv_ok,
            "exit_code": 124,
            "error": None if csv_ok else "timeout_expired",
            "cmd": " ".join(cmd),
            "stdout_tail": (exc.stdout or "").strip()[-500:] if exc.stdout else "",
            "stderr_tail": (exc.stderr or "").strip()[-500:] if exc.stderr else "",
        }
    csv_ok = out_csv.is_file() and out_csv.stat().st_size > 0
    return {
        "ok": proc.returncode == 0 and csv_ok,
        "partial_csv": csv_ok and proc.returncode != 0,
        "exit_code": proc.returncode,
        "cmd": " ".join(cmd),
        "stdout_tail": (proc.stdout or "").strip()[-500:],
        "stderr_tail": (proc.stderr or "").strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="BigSet AGPL-isolated Tier-0 bridge")
    ap.add_argument("--topic-slug", default="benei_haelohim_cross_refs")
    ap.add_argument("--dry-run", action="store_true", help="fixture copy only (default unless --live)")
    ap.add_argument("--live", action="store_true", help="invoke external bigset CLI (BYOK tier_15)")
    ap.add_argument("--rows", type=int, default=10)
    ap.add_argument("--prompt", default=THEOLOGY_PROMPT_TEMPLATE)
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    ap.add_argument("--timeout-sec", type=int, default=900)
    args = ap.parse_args()

    mode = "live" if args.live else "dry_run"
    slug = args.topic_slug.strip().replace(" ", "_")
    csv_out = args.raw_dir / f"bigset_{slug}_tier0_v1.csv"
    md_out = args.raw_dir / f"bigset_{slug}_tier0_v1.md"

    live_result: dict[str, Any] | None = None
    azure_cooldown: dict[str, Any] | None = None
    if args.live:
        azure_cooldown = _azure_rate_limit_cooldown()
        prompt = _resolve_prompt(args.prompt, live=True)
        live_result = _run_live_bigset(
            prompt=prompt,
            rows=max(1, args.rows),
            out_csv=csv_out,
            timeout_sec=args.timeout_sec,
        )
        if not live_result.get("ok") and not live_result.get("partial_csv"):
            doc = {
                "schema": "bigset_agent_bridge_v1",
                "generated_at_utc": _now(),
                "mode": mode,
                "ok": False,
                "research_only": True,
                "send_gate": "HOLD",
                "live_result": live_result,
                "azure_cooldown": azure_cooldown,
                "agpl_isolation": "no_bigset_source_import",
                "reproduce_dry_run": "py scripts/bigset_agent_bridge_v1.py --dry-run",
            }
            args.artifact.parent.mkdir(parents=True, exist_ok=True)
            args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ok": False, "error": live_result.get("error", "live_failed")}, ensure_ascii=False))
            return 1
    else:
        if not FIXTURE_CSV.is_file():
            print(f"missing fixture: {FIXTURE_CSV}", file=sys.stderr)
            return 1
        shutil.copyfile(FIXTURE_CSV, csv_out)

    rows = _read_csv_rows(csv_out)
    rows, normalize_notes = _normalize_rows(rows)
    if normalize_notes:
        _write_csv(rows, csv_out)
    valid, val_errors = _validate_rows(rows)
    _wrap_markdown(csv_out, md_out, topic_slug=slug, mode=mode)

    url_ok = sum(
        1
        for r in rows
        if str(r.get("citation_lock_anchor") or r.get("source_url") or "").startswith("http")
    )
    url_ratio = (url_ok / len(rows)) if rows else 0.0

    doc: dict[str, Any] = {
        "schema": "bigset_agent_bridge_v1",
        "generated_at_utc": _now(),
        "mode": mode,
        "ok": valid and len(rows) > 0,
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "topic_slug": slug,
        "prompt_template": THEOLOGY_PROMPT_TEMPLATE,
        "row_count": len(rows),
        "source_url_present_ratio": round(url_ratio, 4),
        "citation_lock_anchor_present_ratio": round(url_ratio, 4),
        "validation_errors": val_errors,
        "normalization_notes": normalize_notes,
        "outputs": {
            "csv": csv_out.relative_to(ROOT).as_posix(),
            "markdown_wrapper": md_out.relative_to(ROOT).as_posix(),
            "schema": SCHEMA_PATH.relative_to(ROOT).as_posix(),
        },
        "agpl_isolation": {
            "bigset_source_import": False,
            "integration_surface": "subprocess_cli_or_fixture_copy_only",
            "artifact_forward_only": True,
        },
        "cost_tier_note": "live mode = tier_15 BYOK (TinyFish + OpenRouter); dry-run = tier_0",
        "live_result": live_result,
        "azure_cooldown": azure_cooldown,
        "reproduce_dry_run": "py scripts/bigset_agent_bridge_v1.py --dry-run",
        "reproduce_live": "py scripts/bigset_agent_bridge_v1.py --live --rows 10",
    }

    args.artifact.parent.mkdir(parents=True, exist_ok=True)
    args.artifact.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "rows": len(rows), "csv": str(csv_out)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
