#!/usr/bin/env python3
"""B-track prophecy pilot: pre-generation contemplation gate (local bundle guards + digest).

Writes docs/final/artifacts/btrack_prophecy_contemplation_v1_latest.json.
No cloud LLM in v1; budgets are recorded for audit and future Gemini/thinking paths.

Env (optional):
  MKM_BTRACK_CONTEMPLATION_TIMEOUT_SEC  (default 30, wall-clock ceiling for future I/O)
  MKM_BTRACK_CONTEMPLATION_MAX_OUTPUT_TOKENS (default 0 = not used for local route)
  MKM_BTRACK_CONTEMPLATION_MAX_ROUNDS (default 1)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_contemplation_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "btrack_prophecy_contemplation_v1.schema.json"
SCHEMA_ID = "btrack_prophecy_contemplation_v1"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _collect_btc_scope_violations(bundle: dict[str, Any]) -> list[str]:
    arts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    violations: list[str] = []
    if not isinstance(arts, dict):
        return violations

    def _check(name: str, art: Any) -> None:
        if not isinstance(art, dict):
            return
        ts = art.get("trading_scope") if isinstance(art.get("trading_scope"), dict) else {}
        if isinstance(ts, dict):
            pa = str(ts.get("primary_asset") or "").strip().upper()
            if pa and pa != "BTCUSDT":
                violations.append(f"{name}:trading_scope.primary_asset={pa}")
        ps = art.get("policy_scope") if isinstance(art.get("policy_scope"), dict) else {}
        if isinstance(ps, dict):
            pa2 = str(ps.get("trading_primary_asset") or "").strip().upper()
            if pa2 and pa2 != "BTCUSDT":
                violations.append(f"{name}:policy_scope.trading_primary_asset={pa2}")
            kospi_role = str(ps.get("kospi_role") or "").strip().lower()
            if kospi_role and kospi_role != "observation_only":
                violations.append(f"{name}:policy_scope.kospi_role={kospi_role}")

    for k, v in arts.items():
        _check(str(k), v)
    return violations


def _try_jsonschema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    try:
        schema = _load_json(schema_path)
        jsonschema.Draft202012Validator(schema).validate(doc)
    except Exception as e:  # noqa: BLE001
        return [str(e)]
    return []


def _append_audit(
    repo: Path,
    *,
    stage: str,
    decision: str,
    evidence_rel: str,
    note: str,
    skip: bool,
) -> None:
    if skip:
        return
    log_py = repo / "scripts" / "log_agent_decision.py"
    if not log_py.is_file():
        return
    cmd = [
        sys.executable,
        str(log_py),
        "--repo-root",
        str(repo),
        "--mission-id",
        "btrack_prophecy_contemplation_v1",
        "--stage",
        stage,
        "--decision",
        decision,
        "--evidence-path",
        evidence_rel.replace("\\", "/"),
        "--actor",
        "run_btrack_prophecy_contemplation_v1.py",
        "--note",
        note[:3800],
    ]
    subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--repo-root", type=Path, default=ROOT)
    ap.add_argument("--skip-audit-log", action="store_true")
    args = ap.parse_args()

    t0 = time.monotonic()
    try:
        timeout_sec = max(1, int(os.environ.get("MKM_BTRACK_CONTEMPLATION_TIMEOUT_SEC", "30")))
    except ValueError:
        timeout_sec = 30
    try:
        max_out = max(0, int(os.environ.get("MKM_BTRACK_CONTEMPLATION_MAX_OUTPUT_TOKENS", "0")))
    except ValueError:
        max_out = 0
    try:
        max_rounds = max(1, min(8, int(os.environ.get("MKM_BTRACK_CONTEMPLATION_MAX_ROUNDS", "1"))))
    except ValueError:
        max_rounds = 1

    if not args.bundle.is_file():
        print(f"error: bundle missing: {args.bundle}", file=sys.stderr)
        return 1

    bundle = _load_json(args.bundle)
    bundle_sha = _file_sha256(args.bundle)
    try:
        bundle_rel = str(args.bundle.resolve().relative_to(args.repo_root.resolve())).replace("\\", "/")
    except ValueError:
        bundle_rel = str(args.bundle).replace("\\", "/")

    checks: list[dict[str, Any]] = []
    arts_ok = isinstance(bundle.get("artifacts"), dict)
    checks.append({"id": "bundle_artifacts_object", "ok": arts_ok, "detail": None if arts_ok else "artifacts_not_object"})
    violations = _collect_btc_scope_violations(bundle)
    scope_ok = len(violations) == 0
    checks.append(
        {
            "id": "btc_trading_scope_bundle_guard",
            "ok": scope_ok,
            "detail": None if scope_ok else ";".join(violations[:12]),
        }
    )

    elapsed = time.monotonic() - t0
    wall_ok = elapsed <= float(timeout_sec)
    checks.append(
        {
            "id": "wall_clock_within_timeout_sec",
            "ok": wall_ok,
            "detail": f"elapsed_sec={elapsed:.3f}" if wall_ok else f"elapsed_sec={elapsed:.3f}>cap={timeout_sec}",
        }
    )

    all_ok = all(bool(c.get("ok")) for c in checks)
    status = "pass" if all_ok else "fail"
    digest_src = json.dumps(
        {"bundle_sha256": bundle_sha, "checks": checks, "violations": violations},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()
    summary = (
        f"local_bundle_guard_v1 model_route=local_bundle_guard_v1 status={status} "
        f"checks_ok={sum(1 for c in checks if c.get('ok'))}/{len(checks)} violations_n={len(violations)}"
    )[:500]

    doc: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "generated_at_utc": _iso_now(),
        "pilot_lane": "btrack_btc_macro_prophecy",
        "budget": {
            "max_output_tokens": max_out,
            "timeout_sec": timeout_sec,
            "max_rounds": max_rounds,
        },
        "inputs_digest": {
            "bundle_path": bundle_rel,
            "bundle_sha256": bundle_sha,
        },
        "model_route": "local_bundle_guard_v1",
        "review": {
            "status": status,
            "checks": checks,
            "redacted_reasoning_summary": summary,
            "reasoning_digest_sha256": digest,
        },
        "approved_hypothesis_payload": {},
        "downstream": {"compatible_with": "btrack_hypothesis_prophecy_v1"},
    }

    schema_errs = _try_jsonschema(doc, args.schema)
    if schema_errs:
        print("jsonschema:", *schema_errs, sep="\n", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        out_rel = str(args.output.resolve().relative_to(args.repo_root.resolve())).replace("\\", "/")
    except ValueError:
        out_rel = str(args.output).replace("\\", "/")

    _append_audit(
        args.repo_root,
        stage="s1_complete",
        decision=status,
        evidence_rel=out_rel,
        note=summary,
        skip=bool(args.skip_audit_log),
    )

    print(f"WROTE: {args.output.resolve()} review.status={status}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
