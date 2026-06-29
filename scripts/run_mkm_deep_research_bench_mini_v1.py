#!/usr/bin/env python3
"""P2-G: DeepResearch Bench-inspired 7-task mini harness (FACT-lite aggregate gate).

Each task: fixed explore JSONL → LIT_REVIEW → citation_lock [→ fact_support → router_index].
Optional herbs_formulas domain extensions: extract chain + alias resolve.
Track B · research_only · send_gate HOLD · not a full DRB reproduction.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TASKS = ROOT / "tests" / "fixtures" / "mkm_deep_research_bench_tasks_v1.json"
DEFAULT_OUT = ROOT / "reports" / "mkm_deep_research_bench_mini_v1_latest.json"
DEFAULT_OUT_DIR = ROOT / "docs" / "final" / "artifacts" / "dr_bench_mini"
BUILD = ROOT / "scripts" / "build_mkm_deep_explore_lit_review_v1.py"
CITATION_LOCK = ROOT / "scripts" / "check_research_lit_review_citation_lock_v1.py"
FACT_SUPPORT = ROOT / "scripts" / "check_research_lit_review_fact_support_v1.py"
ROUTER_INDEX = ROOT / "scripts" / "build_mkm_deep_research_router_index_v1.py"
HERBS_CHAIN = ROOT / "scripts" / "run_herbs_formulas_extract_chain_v1.py"
DIGESTION_CHAIN = ROOT / "scripts" / "run_mkm_digestion_engine_chain_v1.py"

from scripts.compute_digested_digest_metrics_v1 import compute_digested_digest_metrics  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _difficulty_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"baseline": 0, "challenge": 0}
    for row in rows:
        row_id = str(row.get("row_id") or "")
        if row_id.startswith("challenge-"):
            counts["challenge"] += 1
        else:
            counts["baseline"] += 1
    return counts


def _difficulty_of_row(row: dict[str, Any]) -> str:
    row_id = str(row.get("row_id") or "")
    return "challenge" if row_id.startswith("challenge-") else "baseline"


def _difficulty_pass_metrics(
    rows: list[dict[str, Any]],
    *,
    lock_doc: dict[str, Any],
    fact_doc: dict[str, Any],
    citation_pass_rate: float,
    support_pass_rate: float,
) -> dict[str, dict[str, float | int]]:
    citation_entries = {
        str(e.get("arxiv_id") or ""): str(e.get("status") or "")
        for e in (lock_doc.get("files") or [{}])[0].get("entries", [])
    }
    support_entries = {
        str(e.get("arxiv_id") or ""): str(e.get("support_status") or "")
        for e in fact_doc.get("entries", [])
    }
    out: dict[str, dict[str, float | int]] = {
        "baseline": {"rows": 0, "citation_passed": 0, "support_passed": 0},
        "challenge": {"rows": 0, "citation_passed": 0, "support_passed": 0},
    }
    # CLI summaries can omit per-entry rows; fallback to aggregate rate signal.
    has_entry_level = bool(citation_entries) and bool(support_entries)
    for row in rows:
        aid = str(row.get("arxiv_id") or "")
        diff = _difficulty_of_row(row)
        cell = out[diff]
        cell["rows"] = int(cell["rows"]) + 1
        if has_entry_level:
            if citation_entries.get(aid) in {"verified", "format_only"}:
                cell["citation_passed"] = int(cell["citation_passed"]) + 1
            if support_entries.get(aid) == "supported":
                cell["support_passed"] = int(cell["support_passed"]) + 1
        else:
            if citation_pass_rate >= 1.0:
                cell["citation_passed"] = int(cell["citation_passed"]) + 1
            if support_pass_rate >= 1.0:
                cell["support_passed"] = int(cell["support_passed"]) + 1
    for diff in ("baseline", "challenge"):
        cell = out[diff]
        rows_n = int(cell["rows"])
        cell["citation_pass_rate"] = round(int(cell["citation_passed"]) / rows_n, 4) if rows_n else 0.0
        cell["support_pass_rate"] = round(int(cell["support_passed"]) / rows_n, 4) if rows_n else 0.0
    out["_source"] = {"mode": "entries" if has_entry_level else "summary_fallback"}
    return out


def load_tasks(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "mkm_deep_research_bench_tasks_v1":
        raise ValueError(f"unexpected tasks schema in {path}")
    return doc


def _load_artifact_doc_from_summary(summary_doc: dict[str, Any]) -> dict[str, Any]:
    out_path = summary_doc.get("out_path")
    if not isinstance(out_path, str) or not out_path.strip():
        return summary_doc
    raw_path = Path(out_path)
    artifact_path = raw_path if raw_path.is_absolute() else (ROOT / raw_path)
    if not artifact_path.is_file():
        return summary_doc
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def _load_citation_file_doc(lock_summary: dict[str, Any]) -> dict[str, Any]:
    files = lock_summary.get("files") or []
    if not files:
        return lock_summary
    first = files[0] if isinstance(files[0], dict) else {}
    out_path = first.get("out_path")
    if isinstance(out_path, str) and out_path.strip():
        raw_path = Path(out_path)
        artifact_path = raw_path if raw_path.is_absolute() else (ROOT / raw_path)
        if artifact_path.is_file():
            return json.loads(artifact_path.read_text(encoding="utf-8"))
    return first


def _run_herbs_domain_extensions(
    *,
    task: dict[str, Any],
    task_id: str,
    out_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    if str(task.get("domain_lane") or "") != "herbs_formulas":
        return {"skipped": True, "reason": "not_herbs_formulas_domain"}
    extensions = task.get("extensions") or {}
    if not isinstance(extensions, dict) or not extensions:
        return {"skipped": True, "reason": "no_extensions_configured"}

    steps: dict[str, Any] = {}
    ok = True

    herbs_md = extensions.get("herbs_extract_md")
    if isinstance(herbs_md, str) and herbs_md.strip():
        md_path = (ROOT / herbs_md).resolve()
        chain_out = out_dir / f"{task_id}_herbs_extract_chain_bench.json"
        chain_cmd = [
            sys.executable,
            str(HERBS_CHAIN),
            "--input",
            str(md_path),
            "--out-json",
            str(chain_out),
            "--no-write-locks",
        ]
        if offline:
            chain_cmd.append("--offline")
        chain_proc = _run(chain_cmd)
        steps["herbs_extract_chain"] = {
            "exit_code": chain_proc.returncode,
            "stdout": chain_proc.stdout.strip(),
        }
        if chain_proc.returncode != 0:
            ok = False
        elif chain_out.is_file():
            chain_doc = json.loads(chain_out.read_text(encoding="utf-8"))
            steps["herbs_extract_chain"]["extract_ok"] = chain_doc.get("extract", {}).get("schema")
            steps["herbs_extract_chain"]["doi_lock_ok"] = (chain_doc.get("doi_lock") or {}).get("ok")
            steps["herbs_extract_chain"]["pmid_lock_ok"] = (chain_doc.get("pmid_lock") or {}).get("ok")
            if not chain_doc.get("ok"):
                ok = False

    alias_expect = extensions.get("alias_expect")
    if isinstance(alias_expect, list) and alias_expect:
        from scripts.herbs_formulas_alias_table_v1 import resolve_alias_queries

        queries = [str(row.get("query") or "") for row in alias_expect if isinstance(row, dict)]
        alias_doc = resolve_alias_queries(queries)
        alias_results = {str(r.get("query") or ""): r for r in alias_doc.get("results") or []}
        checks: list[dict[str, Any]] = []
        for expected in alias_expect:
            if not isinstance(expected, dict):
                continue
            query = str(expected.get("query") or "")
            want = str(expected.get("match_type") or "")
            got = str((alias_results.get(query) or {}).get("match_type") or "")
            passed = got == want
            checks.append({"query": query, "expected": want, "actual": got, "ok": passed})
            if not passed:
                ok = False
        steps["alias_resolve"] = {
            "herb_count": alias_doc.get("integrity_flags", {}).get("herb_count"),
            "formula_count": alias_doc.get("integrity_flags", {}).get("formula_count"),
            "checks": checks,
        }

    return {
        "skipped": False,
        "domain_lane": "herbs_formulas",
        "ok": ok,
        "steps": steps,
    }


def _run_digestion_domain_extensions(
    *,
    task: dict[str, Any],
    task_id: str,
    out_dir: Path,
    offline: bool,
) -> dict[str, Any]:
    if str(task.get("domain_lane") or "") != "digestion_engine":
        return {"skipped": True, "reason": "not_digestion_engine_domain"}
    extensions = task.get("extensions") or {}
    if not isinstance(extensions, dict) or not extensions:
        return {"skipped": True, "reason": "no_extensions_configured"}

    digestion_md = extensions.get("digestion_md")
    expect = extensions.get("digestion_expect") or {}
    if not isinstance(digestion_md, str) or not digestion_md.strip():
        return {"skipped": True, "reason": "no_digestion_md"}

    md_path = (ROOT / digestion_md).resolve()
    chain_out = out_dir / f"{task_id}_digestion_chain_bench.json"
    digested_out = out_dir / f"{task_id}_digested_facts_bench.json"
    chain_cmd = [
        sys.executable,
        str(DIGESTION_CHAIN),
        "--input",
        str(md_path),
        "--digested-out",
        str(digested_out),
        "--out-json",
        str(chain_out),
        "--skip-citation-lock",
    ]
    if offline:
        chain_cmd.append("--offline")
    else:
        chain_cmd.append("--production")
    chain_proc = _run(chain_cmd)
    steps: dict[str, Any] = {
        "digestion_chain": {
            "exit_code": chain_proc.returncode,
            "stdout": chain_proc.stdout.strip(),
        }
    }
    ok = chain_proc.returncode == 0
    if not ok:
        return {"skipped": False, "domain_lane": "digestion_engine", "ok": False, "steps": steps}

    chain_doc = json.loads(chain_out.read_text(encoding="utf-8")) if chain_out.is_file() else {}
    digested_doc = json.loads(digested_out.read_text(encoding="utf-8")) if digested_out.is_file() else {}
    pass_metrics = compute_digested_digest_metrics(digested_doc)
    fact_count = int(pass_metrics["fact_count"])
    wired_count = int(pass_metrics["wired_count"])
    gate_ok = bool((chain_doc.get("steps") or {}).get("fact_lock_gate", {}).get("exit_code") == 0)

    checks: dict[str, Any] = {
        "fact_count": fact_count,
        "wired_count": wired_count,
        "gate_ok": gate_ok,
        "chain_ok": bool(chain_doc.get("ok")),
        "digest_pass_metrics": pass_metrics,
    }
    if isinstance(expect, dict):
        min_facts = int(expect.get("min_fact_count") or 0)
        min_wired = int(expect.get("min_wired_count") or 0)
        want_gate = bool(expect.get("gate_ok"))
        min_wiring_rate = float(expect.get("min_wiring_rate") or 0.0)
        min_gate_pass_rate = float(expect.get("min_gate_pass_rate") or 0.0)
        min_verification_right_rate = float(expect.get("min_verification_right_rate") or 0.0)
        checks["expect"] = expect
        if fact_count < min_facts:
            ok = False
            checks["fail_reason"] = f"fact_count {fact_count} < {min_facts}"
        if wired_count < min_wired:
            ok = False
            checks["fail_reason"] = f"wired_count {wired_count} < {min_wired}"
        if want_gate and not gate_ok:
            ok = False
            checks["fail_reason"] = "fact_lock_gate not ok"
        if pass_metrics["wiring_rate"] < min_wiring_rate:
            ok = False
            checks["fail_reason"] = (
                f"wiring_rate {pass_metrics['wiring_rate']} < {min_wiring_rate}"
            )
        if pass_metrics["gate_pass_rate"] < min_gate_pass_rate:
            ok = False
            checks["fail_reason"] = (
                f"gate_pass_rate {pass_metrics['gate_pass_rate']} < {min_gate_pass_rate}"
            )
        if pass_metrics["verification_right_rate"] < min_verification_right_rate:
            ok = False
            checks["fail_reason"] = (
                "verification_right_rate "
                f"{pass_metrics['verification_right_rate']} < {min_verification_right_rate}"
            )
    steps["digestion_checks"] = checks

    return {
        "skipped": False,
        "domain_lane": "digestion_engine",
        "ok": ok,
        "steps": steps,
    }


def run_task(
    *,
    task: dict[str, Any],
    out_dir: Path,
    offline: bool,
    min_pass_rate: float,
    include_router: bool,
) -> dict[str, Any]:
    task_id = str(task["id"])
    query = str(task["query"])
    jsonl = ROOT / str(task["jsonl"])
    if not jsonl.is_file():
        return {
            "id": task_id,
            "ok": False,
            "error": f"missing jsonl: {jsonl}",
        }
    fixture_rows = _load_jsonl_rows(jsonl)
    difficulty_counts = _difficulty_counts(fixture_rows)

    lit_out = out_dir / f"{task_id}_LIT_REVIEW_bench.md"
    build_proc = _run(
        [
            sys.executable,
            str(BUILD),
            "--jsonl",
            str(jsonl),
            "--query",
            query,
            "--out",
            str(lit_out),
        ]
    )
    if build_proc.returncode != 0:
        return {
            "id": task_id,
            "ok": False,
            "step": "build_lit_review",
            "stderr": build_proc.stderr,
            "stdout": build_proc.stdout,
        }

    lock_cmd = [
        sys.executable,
        str(CITATION_LOCK),
        "--input",
        str(lit_out),
        "--min-pass-rate",
        str(min_pass_rate),
    ]
    if offline:
        lock_cmd.append("--offline")
    else:
        lock_cmd.extend(["--min-total-ids", "1"])
    lock_proc = _run(lock_cmd)
    if lock_proc.returncode != 0:
        return {
            "id": task_id,
            "ok": False,
            "step": "citation_lock",
            "stderr": lock_proc.stderr,
            "stdout": lock_proc.stdout,
        }
    lock_summary = json.loads(lock_proc.stdout.strip())
    lock_file = _load_citation_file_doc(lock_summary)
    lock_entries = lock_file.get("entries") or []
    citation_pass_rate = float(lock_file.get("citation_pass_rate") or 0.0)

    fact_cmd = [
        sys.executable,
        str(FACT_SUPPORT),
        "--input",
        str(lit_out),
        "--min-pass-rate",
        str(min_pass_rate),
    ]
    if offline:
        fact_cmd.append("--offline")
    else:
        fact_cmd.extend(["--min-total-claims", "1"])
    fact_proc = _run(fact_cmd)
    if fact_proc.returncode != 0:
        return {
            "id": task_id,
            "ok": False,
            "step": "fact_support",
            "stderr": fact_proc.stderr,
            "stdout": fact_proc.stdout,
        }
    fact_summary = json.loads(fact_proc.stdout.strip())
    fact_doc = _load_artifact_doc_from_summary(fact_summary)
    support_pass_rate = float(fact_doc.get("support_pass_rate") or 0.0)
    difficulty_pass_metrics = _difficulty_pass_metrics(
        fixture_rows,
        lock_doc={"files": [{"entries": lock_entries}]},
        fact_doc=fact_doc,
        citation_pass_rate=citation_pass_rate,
        support_pass_rate=support_pass_rate,
    )
    difficulty_source = (difficulty_pass_metrics.get("_source") or {}).get("mode")
    fallback_used = difficulty_source != "entries"
    fallback_reason = None
    if fallback_used:
        fallback_reason = "missing_entry_level_rows_in_citation_or_fact_artifact"
        _log(f"WARN: dr_bench_mini:{task_id} using summary fallback for difficulty pass metrics")

    router_doc: dict[str, Any] | None = None
    if include_router:
        router_proc = _run(
            [
                sys.executable,
                str(ROUTER_INDEX),
                "--input-md",
                str(lit_out),
                "--query",
                query,
                "--stdout-only",
            ]
        )
        if router_proc.returncode != 0:
            return {
                "id": task_id,
                "ok": False,
                "step": "router_index",
                "stderr": router_proc.stderr,
                "stdout": router_proc.stdout,
            }
        router_doc = json.loads(router_proc.stdout.strip())

    expected_plane = str(task.get("research_plane") or "")
    plane_match = (
        router_doc is not None and str(router_doc.get("research_plane") or "") == expected_plane
        if expected_plane and router_doc
        else None
    )

    task_ok = citation_pass_rate >= min_pass_rate and support_pass_rate >= min_pass_rate
    herbs_ext = _run_herbs_domain_extensions(
        task=task,
        task_id=task_id,
        out_dir=out_dir,
        offline=offline,
    )
    if not herbs_ext.get("skipped") and not herbs_ext.get("ok"):
        task_ok = False

    digestion_ext = _run_digestion_domain_extensions(
        task=task,
        task_id=task_id,
        out_dir=out_dir,
        offline=offline,
    )
    if not digestion_ext.get("skipped") and not digestion_ext.get("ok"):
        task_ok = False

    return {
        "id": task_id,
        "label": task.get("label"),
        "query": query,
        "jsonl": _posix_path(jsonl),
        "lit_review_md": _posix_path(lit_out),
        "citation_pass_rate": citation_pass_rate,
        "support_pass_rate": support_pass_rate,
        "citation_total_ids": lock_file.get("total_ids"),
        "support_total_claims": fact_doc.get("total_claims"),
        "research_plane_expected": expected_plane or None,
        "research_plane_actual": (router_doc or {}).get("research_plane"),
        "research_plane_match": plane_match,
        "fixture_rows": len(fixture_rows),
        "difficulty_counts": difficulty_counts,
        "difficulty_pass_metrics": difficulty_pass_metrics,
        "difficulty_pass_metrics_source": difficulty_source,
        "difficulty_pass_metrics_fallback_used": fallback_used,
        "difficulty_pass_metrics_fallback_reason": fallback_reason,
        "herbs_domain_extensions": herbs_ext if not herbs_ext.get("skipped") else None,
        "digestion_domain_extensions": digestion_ext if not digestion_ext.get("skipped") else None,
        "ok": task_ok,
    }


def aggregate_results(
    *,
    task_results: list[dict[str, Any]],
    min_citation: float,
    min_support: float,
    require_entry_level: bool,
    min_difficulty_baseline_citation: float = 0.85,
    min_difficulty_baseline_support: float = 0.85,
    min_difficulty_challenge_citation: float = 0.8,
    min_difficulty_challenge_support: float = 0.8,
    min_digestion_gate_pass_rate_mean: float = 1.0,
    require_digestion_tasks_ok: bool = True,
) -> dict[str, Any]:
    ok_tasks = [t for t in task_results if t.get("ok")]
    citation_rates = [float(t["citation_pass_rate"]) for t in task_results if "citation_pass_rate" in t]
    support_rates = [float(t["support_pass_rate"]) for t in task_results if "support_pass_rate" in t]
    citation_mean = sum(citation_rates) / len(citation_rates) if citation_rates else 0.0
    support_mean = sum(support_rates) / len(support_rates) if support_rates else 0.0
    baseline_rows = sum(int((t.get("difficulty_counts") or {}).get("baseline", 0)) for t in task_results)
    challenge_rows = sum(int((t.get("difficulty_counts") or {}).get("challenge", 0)) for t in task_results)
    fallback_used_count = sum(1 for t in task_results if t.get("difficulty_pass_metrics_fallback_used"))
    baseline_citation = sum(
        float(((t.get("difficulty_pass_metrics") or {}).get("baseline") or {}).get("citation_passed", 0))
        for t in task_results
    )
    challenge_citation = sum(
        float(((t.get("difficulty_pass_metrics") or {}).get("challenge") or {}).get("citation_passed", 0))
        for t in task_results
    )
    baseline_support = sum(
        float(((t.get("difficulty_pass_metrics") or {}).get("baseline") or {}).get("support_passed", 0))
        for t in task_results
    )
    challenge_support = sum(
        float(((t.get("difficulty_pass_metrics") or {}).get("challenge") or {}).get("support_passed", 0))
        for t in task_results
    )
    diff_baseline_citation = round((baseline_citation / baseline_rows), 4) if baseline_rows else 0.0
    diff_baseline_support = round((baseline_support / baseline_rows), 4) if baseline_rows else 0.0
    diff_challenge_citation = round((challenge_citation / challenge_rows), 4) if challenge_rows else 0.0
    diff_challenge_support = round((challenge_support / challenge_rows), 4) if challenge_rows else 0.0
    difficulty_gate_ok = (
        (baseline_rows == 0 or diff_baseline_citation >= min_difficulty_baseline_citation)
        and (baseline_rows == 0 or diff_baseline_support >= min_difficulty_baseline_support)
        and (challenge_rows == 0 or diff_challenge_citation >= min_difficulty_challenge_citation)
        and (challenge_rows == 0 or diff_challenge_support >= min_difficulty_challenge_support)
    )
    digestion_pass_metrics: dict[str, Any] | None = None
    digestion_tasks = [
        t
        for t in task_results
        if isinstance(t.get("digestion_domain_extensions"), dict)
        and not t["digestion_domain_extensions"].get("skipped")
    ]
    if digestion_tasks:
        agg = {
            "task_count": len(digestion_tasks),
            "fact_count": 0,
            "wired_count": 0,
            "verification_right_count": 0,
            "gate_pass_count": 0,
            "gate_fail_count": 0,
        }
        for t in digestion_tasks:
            dm = (
                ((t.get("digestion_domain_extensions") or {}).get("steps") or {})
                .get("digestion_checks", {})
                .get("digest_pass_metrics")
            ) or {}
            agg["fact_count"] += int(dm.get("fact_count") or 0)
            agg["wired_count"] += int(dm.get("wired_count") or 0)
            agg["verification_right_count"] += int(dm.get("verification_right_count") or 0)
            agg["gate_pass_count"] += int(dm.get("gate_pass_count") or 0)
            agg["gate_fail_count"] += int(dm.get("gate_fail_count") or 0)
        fc = agg["fact_count"]
        ge = agg["gate_pass_count"] + agg["gate_fail_count"]
        digestion_pass_metrics = {
            **agg,
            "wiring_rate_mean": round(agg["wired_count"] / fc, 4) if fc else 0.0,
            "verification_right_rate_mean": round(agg["verification_right_count"] / fc, 4) if fc else 0.0,
            "gate_pass_rate_mean": round(agg["gate_pass_count"] / ge, 4) if ge else 0.0,
            "tasks_all_ok": all(bool(t.get("ok")) for t in digestion_tasks),
        }
    digestion_gate_ok = (
        digestion_pass_metrics is None
        or (
            (not require_digestion_tasks_ok or bool(digestion_pass_metrics.get("tasks_all_ok")))
            and float(digestion_pass_metrics.get("gate_pass_rate_mean") or 0.0)
            >= min_digestion_gate_pass_rate_mean
        )
    )
    gate_ok = (
        len(ok_tasks) == len(task_results)
        and task_results
        and citation_mean >= min_citation
        and support_mean >= min_support
        and (not require_entry_level or fallback_used_count == 0)
        and difficulty_gate_ok
        and digestion_gate_ok
    )
    return {
        "task_count": len(task_results),
        "tasks_ok": len(ok_tasks),
        "citation_pass_rate_mean": round(citation_mean, 4),
        "support_pass_rate_mean": round(support_mean, 4),
        "difficulty_rows_total": {
            "baseline": baseline_rows,
            "challenge": challenge_rows,
        },
        "difficulty_pass_rate": {
            "baseline": {
                "citation": diff_baseline_citation,
                "support": diff_baseline_support,
            },
            "challenge": {
                "citation": diff_challenge_citation,
                "support": diff_challenge_support,
            },
        },
        "difficulty_gate_ok": difficulty_gate_ok,
        "difficulty_entry_mapping": {
            "fallback_used_task_count": fallback_used_count,
            "all_tasks_entry_level": fallback_used_count == 0,
            "require_entry_level": require_entry_level,
        },
        "min_aggregate_citation_pass_rate": min_citation,
        "min_aggregate_support_pass_rate": min_support,
        "min_difficulty_baseline_citation_pass_rate": min_difficulty_baseline_citation,
        "min_difficulty_baseline_support_pass_rate": min_difficulty_baseline_support,
        "min_difficulty_challenge_citation_pass_rate": min_difficulty_challenge_citation,
        "min_difficulty_challenge_support_pass_rate": min_difficulty_challenge_support,
        "digestion_pass_metrics": digestion_pass_metrics,
        "digestion_gate_ok": digestion_gate_ok,
        "min_digestion_gate_pass_rate_mean": min_digestion_gate_pass_rate_mean,
        "require_digestion_tasks_ok": require_digestion_tasks_ok,
        "gate_ok": gate_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepResearch Bench mini harness (6-task FACT-lite smoke)")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--offline", action="store_true", help="Format-only citation + offline fact (CI default)")
    parser.add_argument("--min-pass-rate", type=float, default=0.85)
    parser.add_argument("--include-router", action="store_true")
    parser.add_argument(
        "--require-entry-level",
        action="store_true",
        help="Fail gate if any task used summary fallback for difficulty pass metrics",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    tasks_path = args.tasks.resolve()
    if not tasks_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing tasks: {tasks_path}"}, ensure_ascii=False))
        return 2

    spec = load_tasks(tasks_path)
    min_citation = float(spec.get("min_aggregate_citation_pass_rate") or args.min_pass_rate)
    min_support = float(spec.get("min_aggregate_support_pass_rate") or args.min_pass_rate)
    min_diff_baseline_citation = float(
        spec.get("min_difficulty_baseline_citation_pass_rate") or min_citation
    )
    min_diff_baseline_support = float(
        spec.get("min_difficulty_baseline_support_pass_rate") or min_support
    )
    min_diff_challenge_citation = float(
        spec.get("min_difficulty_challenge_citation_pass_rate") or 0.8
    )
    min_diff_challenge_support = float(
        spec.get("min_difficulty_challenge_support_pass_rate") or 0.8
    )
    min_digestion_gate_pass_rate = float(spec.get("min_digestion_gate_pass_rate_mean") or 1.0)
    require_digestion_tasks_ok = bool(spec.get("require_digestion_tasks_ok", True))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    task_results: list[dict[str, Any]] = []
    for task in spec.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        _log(f"dr_bench_mini: task {task.get('id')}")
        task_results.append(
            run_task(
                task=task,
                out_dir=args.out_dir.resolve(),
                offline=args.offline,
                min_pass_rate=args.min_pass_rate,
                include_router=args.include_router,
            )
        )

    metrics = aggregate_results(
        task_results=task_results,
        min_citation=min_citation,
        min_support=min_support,
        require_entry_level=args.require_entry_level,
        min_difficulty_baseline_citation=min_diff_baseline_citation,
        min_difficulty_baseline_support=min_diff_baseline_support,
        min_difficulty_challenge_citation=min_diff_challenge_citation,
        min_difficulty_challenge_support=min_diff_challenge_support,
        min_digestion_gate_pass_rate_mean=min_digestion_gate_pass_rate,
        require_digestion_tasks_ok=require_digestion_tasks_ok,
    )
    doc = {
        "schema": "mkm_deep_research_bench_mini_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": metrics["gate_ok"],
        "tasks_spec": _posix_path(tasks_path),
        "mode": "offline" if args.offline else "online",
        "metrics": metrics,
        "tasks": task_results,
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "policy": "DeepResearch Bench-inspired mini harness; aggregate FACT-lite only",
        "reproduce": f"py scripts/run_mkm_deep_research_bench_mini_v1.py --offline --tasks {_posix_path(tasks_path)}",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "out_json": _posix_path(args.out_json),
                "task_count": metrics["task_count"],
                "tasks_ok": metrics["tasks_ok"],
                "citation_pass_rate_mean": metrics["citation_pass_rate_mean"],
                "support_pass_rate_mean": metrics["support_pass_rate_mean"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
