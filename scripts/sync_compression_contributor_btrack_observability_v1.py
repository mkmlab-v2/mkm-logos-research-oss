#!/usr/bin/env python3
"""Sync contributor bridge signoff → B-track observability bundle + agent_decisions_log (+ optional Vault).

Does NOT merge B→A, mutate active report, or trigger explore/training. Append-only observability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "reports/compression_contributor_btrack_obs_bundle_v1_latest.json"
DEFAULT_MIRROR_REPORT = ROOT / "reports/compression_contributor_vault_mirror_v1_latest.json"
AGENT_LOG = ROOT / "reports/agent_decisions_log.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_repo_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve() if p.is_file() else None


def _vault_contributor_dir() -> Path | None:
    g = Path("G:/")
    if not g.is_dir():
        return None
    try:
        for vault in g.rglob("vault"):
            if vault.is_dir() and "MKM_DATA_VAULT" in vault.as_posix():
                target = vault / "btrack_artifacts_verified" / "compression_contributor"
                return target
    except OSError:
        return None
    return None


def _collect_artifact_paths(
    signoff: dict[str, Any],
    evidence: dict[str, Any],
    candidate: dict[str, Any] | None,
) -> list[Path]:
    paths: list[Path] = []
    for raw in (
        signoff.get("candidate_path"),
        evidence.get("latest_signoff"),
        (evidence.get("candidate_snapshot") or {}).get("path"),
        signoff.get("contributor_jsonl"),
        ((candidate or {}).get("inputs") or {}).get("validate_json"),
        ((candidate or {}).get("inputs") or {}).get("poc_json"),
        ((candidate or {}).get("inputs") or {}).get("contributor_jsonl"),
    ):
        p = _resolve_repo_path(str(raw)) if raw else None
        if p and p not in paths:
            paths.append(p)
    return paths


def build_bundle(
    *,
    signoff_path: Path,
    evidence_path: Path,
    candidate_path: Path | None,
    out_path: Path,
) -> dict[str, Any]:
    signoff = _load(signoff_path)
    evidence = _load(evidence_path)
    candidate = _load(candidate_path) if candidate_path and candidate_path.is_file() else None
    rehearsal_only = bool((candidate or {}).get("rehearsal_only"))
    tenant_id = signoff.get("tenant_id") or (candidate or {}).get("tenant_id")
    contributor_jsonl = signoff.get("contributor_jsonl")
    contrib_path = _resolve_repo_path(str(contributor_jsonl)) if contributor_jsonl else None

    artifacts = _collect_artifact_paths(signoff, evidence, candidate)
    doc: dict[str, Any] = {
        "schema": "compression_contributor_btrack_obs_bundle_v1",
        "generated_at_utc": _utc(),
        "lane": "contributor_provided",
        "track": "btrack_research_only",
        "rehearsal_only": rehearsal_only,
        "tenant_id": tenant_id,
        "auto_track_a_promotion_allowed": False,
        "btrack_learning_material": True,
        "forbidden": ["auto_bridge_b_to_a", "auto_active_report_write", "send_gate_release"],
        "signoff_json": _rel(signoff_path),
        "evidence_json": _rel(evidence_path),
        "candidate_json": _rel(candidate_path) if candidate_path and candidate_path.is_file() else None,
        "contributor_jsonl": contributor_jsonl,
        "contributor_jsonl_sha256": _sha256_file(contrib_path) if contrib_path else signoff.get("validate_sha256"),
        "metrics_at_apply": signoff.get("metrics_at_apply") or (candidate or {}).get("metrics"),
        "promotion_gates_at_apply": signoff.get("promotion_gates_at_apply") or (candidate or {}).get("promotion_gates"),
        "artifact_paths": [_rel(p) for p in artifacts],
        "boundary_ack": (
            "B-track observability bundle for contributor lane — fermentation input only; "
            "not training auto-trigger or Track A promotion."
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def mirror_to_vault(bundle_path: Path, artifact_paths: list[Path]) -> dict[str, Any]:
    vault_dir = _vault_contributor_dir()
    if vault_dir is None:
        return {
            "mirror_ok": False,
            "skipped": True,
            "reason": "vault_not_mounted",
            "target_dir": None,
        }
    vault_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    for src in [bundle_path, *artifact_paths]:
        if not src.is_file():
            missing.append(_rel(src))
            continue
        dst = vault_dir / src.name
        shutil.copy2(src, dst)
        copied.append(dst.name)
    manifest = {
        "schema": "compression_contributor_vault_mirror_v1",
        "mirrored_at_utc": _utc(),
        "mirror_ok": True,
        "skipped": False,
        "target_dir": str(vault_dir).replace("\\", "/"),
        "copied_files": copied,
        "missing_files": missing,
        "bundle_path": _rel(bundle_path),
    }
    (vault_dir / "_compression_contributor_mirror_latest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def append_agent_log(*, bundle_rel: str, rehearsal_only: bool, tenant_id: str | None, actor: str) -> int:
    note = (
        f"contributor_btrack_obs_sync rehearsal_only={rehearsal_only} tenant={tenant_id or 'unknown'}; "
        "no B→A auto-merge"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/log_agent_decision.py"),
            "--mission-id",
            "compression_contributor_btrack_obs_v1",
            "--stage",
            "Report",
            "--decision",
            "contributor_bridge_obs_sync",
            "--evidence-path",
            bundle_rel,
            "--actor",
            actor,
            "--risk-level",
            "low",
            "--note",
            note,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, required=True)
    ap.add_argument("--evidence-json", type=Path, required=True)
    ap.add_argument("--candidate-json", type=Path, default=None)
    ap.add_argument("--bundle-out", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--mirror-report", type=Path, default=DEFAULT_MIRROR_REPORT)
    ap.add_argument("--mirror-vault", action="store_true", help="Copy bundle+artifacts to G: vault when mounted.")
    ap.add_argument("--skip-agent-log", action="store_true")
    ap.add_argument("--actor", default="athena_apply_hook")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    signoff_path = args.signoff_json.resolve()
    evidence_path = args.evidence_json.resolve()
    if not signoff_path.is_file():
        print(f"error: missing signoff: {signoff_path}", file=sys.stderr)
        return 2
    if not evidence_path.is_file():
        print(f"error: missing evidence: {evidence_path}", file=sys.stderr)
        return 2

    candidate_path = args.candidate_json.resolve() if args.candidate_json else None
    if candidate_path is None:
        signoff = _load(signoff_path)
        cand_raw = signoff.get("candidate_path")
        if cand_raw:
            candidate_path = _resolve_repo_path(str(cand_raw))

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "signoff": _rel(signoff_path),
                    "evidence": _rel(evidence_path),
                    "candidate": _rel(candidate_path) if candidate_path else None,
                    "mirror_vault": bool(args.mirror_vault),
                },
                ensure_ascii=False,
            )
        )
        return 0

    bundle = build_bundle(
        signoff_path=signoff_path,
        evidence_path=evidence_path,
        candidate_path=candidate_path,
        out_path=args.bundle_out.resolve(),
    )
    bundle_path = args.bundle_out.resolve()
    artifact_paths = [_resolve_repo_path(p) for p in bundle.get("artifact_paths", [])]
    artifact_paths = [p for p in artifact_paths if p is not None]

    mirror_result: dict[str, Any] = {"mirror_ok": False, "skipped": True, "reason": "mirror_not_requested"}
    if args.mirror_vault:
        mirror_result = mirror_to_vault(bundle_path, artifact_paths)

    args.mirror_report.parent.mkdir(parents=True, exist_ok=True)
    args.mirror_report.write_text(json.dumps(mirror_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_exit = 0
    if not args.skip_agent_log:
        log_exit = append_agent_log(
            bundle_rel=_rel(bundle_path),
            rehearsal_only=bool(bundle.get("rehearsal_only")),
            tenant_id=bundle.get("tenant_id"),
            actor=args.actor,
        )

    print(
        json.dumps(
            {
                "bundle": _rel(bundle_path),
                "mirror": mirror_result,
                "agent_log_exit": log_exit,
                "rehearsal_only": bundle.get("rehearsal_only"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if log_exit == 0 else log_exit


if __name__ == "__main__":
    raise SystemExit(main())
