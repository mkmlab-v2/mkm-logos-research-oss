#!/usr/bin/env python3
"""Human-gated apply for contributor → Track A bridge signoff (does not auto-write active report).

Requires ``--human-approve-promotion``. Records commander approval + corpus hash;
optional ``--also-apply-multilens-active`` chains to multilens apply (second human gate).
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
DEFAULT_CANDIDATE = ROOT / "docs/final/artifacts/compression_contributor_promotion_candidate_v1_latest.json"
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/compression_contributor_track_a_signoff_v1_latest.json"
DEFAULT_EVIDENCE = ROOT / "docs/final/artifacts/compression_contributor_track_a_evidence_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate-json", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--evidence-json", type=Path, default=DEFAULT_EVIDENCE)
    ap.add_argument("--human-approve-promotion", action="store_true")
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    ap.add_argument(
        "--also-apply-multilens-active",
        action="store_true",
        help="After bridge signoff, invoke multilens apply (requires separate multilens candidate).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--skip-obs-sync",
        action="store_true",
        help="Skip B-track observability bundle + agent_decisions_log (default: sync after apply).",
    )
    ap.add_argument(
        "--mirror-vault",
        action="store_true",
        help="When obs sync runs, mirror bundle to G: vault if mounted (never fails apply if absent).",
    )
    args = ap.parse_args()

    if not args.human_approve_promotion:
        print("error: --human-approve-promotion required", file=sys.stderr)
        return 2

    cand_path = args.candidate_json.resolve()
    if not cand_path.is_file():
        print(f"error: missing candidate: {cand_path}", file=sys.stderr)
        return 2

    cand = _load(cand_path)
    gates = cand.get("promotion_gates") or {}
    if not cand.get("commander_may_apply_track_a_bridge"):
        print(
            json.dumps(
                {
                    "denied": True,
                    "reason": "promotion_gates_not_met",
                    "gates": gates,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2

    signoff = {
        "schema": "compression_contributor_track_a_signoff_v1",
        "approved_at_utc": _utc(),
        "reviewer": args.reviewer,
        "note": args.note,
        "candidate_path": _rel(cand_path),
        "tenant_id": cand.get("tenant_id"),
        "contributor_jsonl": (cand.get("inputs") or {}).get("contributor_jsonl"),
        "validate_sha256": (cand.get("inputs") or {}).get("validate_sha256"),
        "promotion_gates_at_apply": gates,
        "metrics_at_apply": cand.get("metrics"),
        "human_approval": {
            "commander_approve_promotion": True,
            "auto_track_a_promotion_allowed": False,
            "active_report_modified_by_this_script": False,
        },
        "boundary_ack": cand.get("boundary_ack"),
    }

    evidence = {
        "schema": "compression_contributor_track_a_evidence_v1",
        "updated_at_utc": _utc(),
        "status": "commander_approved_btrack_to_track_a_bridge",
        "lane": "contributor_provided",
        "latest_signoff": _rel(args.signoff_json),
        "candidate_snapshot": {
            "path": _rel(cand_path),
            "metrics": cand.get("metrics"),
            "track_a_baseline_readonly": cand.get("track_a_baseline_readonly"),
        },
        "next_steps": [
            "Run multilens promotion sweep if codec/active-profile change is intended.",
            "B-track obs: scripts/sync_compression_contributor_btrack_observability_v1.py (auto after apply unless --skip-obs-sync).",
        ],
    }
    if cand.get("rehearsal_only"):
        evidence["rehearsal_only"] = True
        signoff["rehearsal_only"] = True

    if args.dry_run:
        print(json.dumps({"dry_run": True, "signoff": signoff, "evidence": evidence}, ensure_ascii=False))
        return 0

    args.signoff_json.parent.mkdir(parents=True, exist_ok=True)
    args.signoff_json.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.evidence_json.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    obs_exit = 0
    if not args.skip_obs_sync:
        obs_args = [
            sys.executable,
            str(ROOT / "scripts/sync_compression_contributor_btrack_observability_v1.py"),
            "--signoff-json",
            str(args.signoff_json.resolve()),
            "--evidence-json",
            str(args.evidence_json.resolve()),
            "--candidate-json",
            str(cand_path),
            "--actor",
            f"apply_compression_contributor:{args.reviewer}",
        ]
        if args.mirror_vault:
            obs_args.append("--mirror-vault")
        if cand.get("rehearsal_only"):
            obs_args.extend(["--bundle-out", str(ROOT / "reports/compression_contributor_btrack_obs_bundle_plumbing_rehearsal_v1_latest.json")])
        obs_proc = subprocess.run(obs_args, cwd=str(ROOT))
        obs_exit = obs_proc.returncode

    multilens_exit: int | None = None
    final = obs_exit
    if args.also_apply_multilens_active:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/apply_multilens_ultra_compression_track_a_promotion_v1.py"),
                "--human-approve-promotion",
                f"--reviewer={args.reviewer}",
            ],
            cwd=str(ROOT),
        )
        multilens_exit = proc.returncode
        if multilens_exit != 0:
            final = multilens_exit

    print(
        json.dumps(
            {
                "applied_bridge_signoff": _rel(args.signoff_json),
                "evidence": _rel(args.evidence_json),
                "obs_sync_exit": obs_exit if not args.skip_obs_sync else None,
                "multilens_chained": bool(args.also_apply_multilens_active),
                "multilens_exit_code": multilens_exit,
            },
            ensure_ascii=False,
        )
    )
    return 0 if final == 0 else final


if __name__ == "__main__":
    raise SystemExit(main())
