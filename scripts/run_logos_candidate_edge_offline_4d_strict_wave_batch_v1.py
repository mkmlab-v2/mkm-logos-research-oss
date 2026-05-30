#!/usr/bin/env python3
"""Run offline_4d strict micro-batch waves in a loop (defer-only, no canonical merge). [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
DEFAULT_PROGRESS = ROOT / "reports/logos_candidate_edge_wave1_wave2_progress_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_candidate_edge_offline_4d_strict_wave_batch_v1_latest.json"

BATCH_SCRIPT = ROOT / "scripts/build_logos_candidate_edge_offline_4d_strict_batch_v1.py"
PACK_SCRIPT = ROOT / "scripts/build_logos_offline_4d_strict_review_pack_v1.py"
APPLY_SCRIPT = ROOT / "scripts/apply_logos_candidate_edge_human_review_decisions_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _run(cmd: list[str], *, timeout: int = 300) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    out = (proc.stdout or proc.stderr or "").strip()
    return int(proc.returncode), out


def wave_ranks(wave: int, *, batch_size: int = 5, offline_start_rank: int = 46) -> list[int]:
    start = offline_start_rank + (wave - 2) * batch_size
    return list(range(start, start + batch_size))


def _books_from_pair(pair_key: str) -> list[str]:
    books: list[str] = []
    for part in str(pair_key).split("|"):
        if "::" in part:
            ref = part.split("::", 1)[1]
            if "." in ref:
                books.append(ref.split(".", 1)[0])
    return books


def _classify_ranks(items: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
    cross: list[int] = []
    intra: list[int] = []
    for row in items:
        rank = row.get("queue_rank")
        if rank is None:
            continue
        books = _books_from_pair(str(row.get("pair_key") or ""))
        if len(set(books)) > 1:
            cross.append(int(rank))
        else:
            intra.append(int(rank))
    return cross, intra


def _write_closure(
    *,
    wave: int,
    ranks: list[int],
    items: list[dict[str, Any]],
    stats: dict[str, Any],
) -> Path:
    cross, intra = _classify_ranks(items)
    summary: dict[str, Any] = {
        "ranks": ranks,
        "decision": "defer",
        "count": len(ranks),
        "canonical_delta": 0,
    }
    if cross:
        summary["cross_book_deferred"] = cross
    if intra:
        summary["intra_book_deferred"] = intra

    payload = {
        "schema": f"logos_candidate_edge_offline_4d_strict_wave{wave}_closure_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "bulk_merge_blocked": True,
        "wave": wave,
        f"wave{wave}_human_review_closed": True,
        "reviewer": f"commander_offline_4d_strict_wave{wave}",
        "decision_summary": summary,
        "rationale_ko": "sim≈0.99995 — offline_4d strict batch defer_maintain (batch runner).",
        "queue_stats_after": {
            "approved_count": stats.get("approved_count"),
            "deferred_count": stats.get("deferred_count"),
            "pending_count": stats.get("pending_count"),
        },
        "artifacts": {
            "review_pack_md": f"reports/logos_offline_4d_strict_review_pack_wave{wave}_v1_latest.md",
            "strict_batch": f"reports/logos_candidate_edge_offline_4d_lora_strict_batch_wave{wave}_v1_latest.json",
        },
    }
    out = ROOT / f"reports/logos_candidate_edge_offline_4d_strict_wave{wave}_closure_v1_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def _run_single_wave(
    wave: int,
    *,
    batch_size: int,
    decision: str,
    reviewer_prefix: str,
    dry_run: bool,
) -> dict[str, Any]:
    ranks = wave_ranks(wave, batch_size=batch_size)
    rank_csv = ",".join(str(r) for r in ranks)
    reviewer = f"{reviewer_prefix}_wave{wave}"

    batch_json = ROOT / f"reports/logos_candidate_edge_offline_4d_lora_strict_batch_wave{wave}_v1_latest.json"
    subset_json = ROOT / f"docs/final/artifacts/logos_review_queue_offline_4d_strict_wave{wave}_v1_latest.json"
    pack_json = ROOT / f"reports/logos_offline_4d_strict_review_pack_wave{wave}_v1_latest.json"
    pack_md = ROOT / f"reports/logos_offline_4d_strict_review_pack_wave{wave}_v1_latest.md"

    step_log: list[dict[str, Any]] = []

    code, out = _run(
        [
            sys.executable,
            str(BATCH_SCRIPT),
            "--output-batch-json",
            str(batch_json),
            "--output-filtered-json",
            str(subset_json),
            "--max-batch-size",
            str(batch_size),
        ]
    )
    step_log.append({"step": "strict_batch", "exit_code": code, "tail": out[-400:]})
    if code != 0:
        return {"wave": wave, "ok": False, "exit_code": code, "steps": step_log}

    batch_doc = _read_json(batch_json)
    items = batch_doc.get("items") or []
    if not items:
        return {"wave": wave, "ok": True, "exit_code": 0, "empty_batch": True, "steps": step_log}

    if dry_run:
        return {
            "wave": wave,
            "ok": True,
            "dry_run": True,
            "ranks": ranks,
            "items": len(items),
            "steps": step_log,
        }

    for step_name, pack_args in (
        ("review_pack_pre", []),
        ("apply_defer", ["--decision", decision, "--reviewer", reviewer, "--queue-ranks", rank_csv]),
        ("review_pack_post", []),
    ):
        if step_name.startswith("review_pack"):
            cmd = [
                sys.executable,
                str(PACK_SCRIPT),
                "--wave",
                str(wave),
                "--subset-json",
                str(subset_json),
                "--batch-json",
                str(batch_json),
                "--output-json",
                str(pack_json),
                "--output-md",
                str(pack_md),
            ]
        else:
            cmd = [sys.executable, str(APPLY_SCRIPT), *pack_args]
        code, out = _run(cmd)
        step_log.append({"step": step_name, "exit_code": code, "tail": out[-400:]})
        if code != 0:
            return {"wave": wave, "ok": False, "exit_code": code, "steps": step_log}

    subset = _read_json(subset_json)
    queue = _read_json(DEFAULT_QUEUE)
    stats = queue.get("stats") or {}
    closure_path = _write_closure(
        wave=wave,
        ranks=ranks,
        items=subset.get("items") or items,
        stats=stats,
    )
    return {
        "wave": wave,
        "ok": True,
        "exit_code": 0,
        "ranks": ranks,
        "closure": str(closure_path.relative_to(ROOT)).replace("\\", "/"),
        "steps": step_log,
    }


def _update_progress(*, start_wave: int, end_wave: int, waves_run: list[dict[str, Any]], chain_out: Path) -> None:
    progress = _read_json(DEFAULT_PROGRESS)
    queue = _read_json(DEFAULT_QUEUE)
    stats = queue.get("stats") or {}

    deferred_ranks = list(range(46, 546))
    progress["generated_at_utc"] = _utc_now()
    progress["queue_stats"] = {
        **(progress.get("queue_stats") or {}),
        "pending_count": stats.get("pending_count"),
        "approved_count": stats.get("approved_count"),
        "rejected_count": stats.get("rejected_count"),
        "deferred_count": stats.get("deferred_count"),
    }
    progress["offline_4d_strict_deferred_ranks"] = deferred_ranks
    progress["offline_4d_strict_batch_run"] = str(chain_out.relative_to(ROOT)).replace("\\", "/")
    progress["offline_4d_strict_complete"] = stats.get("pending_count") == 0
    progress["offline_4d_strict_batch_summary"] = {
        "start_wave": start_wave,
        "end_wave": end_wave,
        "waves_executed": len(waves_run),
        "waves_ok": sum(1 for w in waves_run if w.get("ok")),
        "last_wave": waves_run[-1].get("wave") if waves_run else None,
    }
    for row in waves_run:
        w = row.get("wave")
        if w and row.get("ok") and not row.get("empty_batch"):
            progress[f"offline_4d_strict_wave{w}_closure"] = row.get("closure") or (
                f"reports/logos_candidate_edge_offline_4d_strict_wave{w}_closure_v1_latest.json"
            )

    DEFAULT_PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_PROGRESS.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start-wave", type=int, default=17)
    ap.add_argument("--end-wave", type=int, default=101)
    ap.add_argument("--batch-size", type=int, default=5)
    ap.add_argument("--decision", choices=("defer", "reject", "approve"), default="defer")
    ap.add_argument("--reviewer-prefix", default="commander_offline_4d_strict")
    ap.add_argument("--dry-run", action="store_true", help="Build first batch only; no queue writes")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    start = int(args.start_wave)
    end = int(args.end_wave)
    if start > end:
        print(json.dumps({"ok": False, "error": "start-wave > end-wave"}))
        return 2

    waves_run: list[dict[str, Any]] = []
    exit_code = 0

    for wave in range(start, end + 1):
        result = _run_single_wave(
            wave,
            batch_size=int(args.batch_size),
            decision=str(args.decision),
            reviewer_prefix=str(args.reviewer_prefix),
            dry_run=bool(args.dry_run),
        )
        waves_run.append(result)
        if not result.get("ok"):
            exit_code = int(result.get("exit_code") or 1)
            break
        if result.get("empty_batch"):
            break
        if args.dry_run:
            break

    chain_doc = {
        "schema": "logos_candidate_edge_offline_4d_strict_wave_batch_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "bulk_merge_blocked": True,
        "start_wave": start,
        "end_wave": end,
        "decision": args.decision,
        "exit_code": exit_code,
        "waves": waves_run,
    }

    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.dry_run and exit_code == 0:
        _update_progress(start_wave=start, end_wave=end, waves_run=waves_run, chain_out=out_path)

    print(
        json.dumps(
            {
                "ok": exit_code == 0,
                "waves_run": len(waves_run),
                "chain_out": str(out_path),
                "exit_code": exit_code,
            },
            ensure_ascii=False,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
