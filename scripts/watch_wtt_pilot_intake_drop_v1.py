#!/usr/bin/env python3
"""Poll data/wtt/intake for new customer-masked JSONL and trigger auto intake ([HYPO])."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,48}[a-z0-9]$")
CHECK_PROVENANCE = ROOT / "scripts/check_wtt_pilot_provenance_v1.py"
INTAKE_DIR = ROOT / "data/wtt/intake"
STATE_DEFAULT = ROOT / "reports/wtt_pilot_intake_drop_watch_state_v1.json"
REPORT_DEFAULT = ROOT / "reports/wtt_pilot_intake_drop_watch_v1_latest.json"
AUTO_PS1 = ROOT / "scripts/Invoke-WttPilotIntakeAuto_v1.ps1"
BOOTSTRAP_PREFIX = "wtt_pilot_"
FORBIDDEN_LABELS = frozenset({"pilot_fill_template", "synthetic_spicy", "synthetic_stub"})
INTERNAL_TENANT_STEMS = frozenset(
    {
        "wtt-operator-panel-v1",
        "wtt-customer-stub-v1",
        "wtt-solo-internal-v1",
        "wtt-synthetic-spicy-v1",
    }
)
MIN_SESSIONS = 20


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": "wtt_pilot_intake_drop_watch_state_v1", "processed": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: dict[str, Any]) -> None:
    state["updated_at_utc"] = _utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tenant_from_stem(stem: str) -> str | None:
    return stem if SLUG_RE.match(stem) else None


def _provenance_gate_ok(tenant_id: str, intake_path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [
            sys.executable,
            str(CHECK_PROVENANCE),
            "--tenant-id",
            tenant_id,
            "--intake-jsonl",
            _rel(intake_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True, "ok"
    return False, (proc.stdout or proc.stderr or "provenance_check_failed")[:200]


def _analyze_jsonl(path: Path) -> dict[str, Any]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    issues: list[str] = []
    customer_rows = 0
    for i, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(f"line_{i}_json:{exc}")
            continue
        labels = set(row.get("labels") or [])
        if labels & FORBIDDEN_LABELS:
            issues.append(f"line_{i}_forbidden_labels:{','.join(sorted(labels & FORBIDDEN_LABELS))}")
        if row.get("customer_provided") is True:
            customer_rows += 1

    if len(lines) < MIN_SESSIONS:
        issues.append(f"session_count_lt_{MIN_SESSIONS}:{len(lines)}")
    if customer_rows == 0:
        issues.append("no_customer_provided_rows")

    return {
        "session_count": len(lines),
        "customer_provided_rows": customer_rows,
        "eligible_for_auto_intake": len(issues) == 0,
        "issues": issues,
    }


def _list_intake_candidates(intake_dir: Path) -> list[Path]:
    if not intake_dir.is_dir():
        intake_dir.mkdir(parents=True, exist_ok=True)
        return []
    out: list[Path] = []
    for path in sorted(intake_dir.glob("*.jsonl")):
        if path.name.startswith(BOOTSTRAP_PREFIX):
            continue
        out.append(path.resolve())
    return out


def run_watch(
    *,
    state_path: Path,
    dry_run: bool,
    force_path: Path | None,
    intake_dir: Path | None = None,
) -> dict[str, Any]:
    active_intake = (intake_dir or INTAKE_DIR).resolve()
    state = _load_state(state_path)
    processed: dict[str, Any] = dict(state.get("processed") or {})
    candidates = [force_path.resolve()] if force_path else _list_intake_candidates(active_intake)

    actions: list[dict[str, Any]] = []
    last_exit = 0

    for path in candidates:
        if not path.is_file():
            actions.append({"path": _rel(path), "action": "skip", "reason": "missing"})
            continue

        digest = _sha256(path)
        key = _rel(path)
        prior = processed.get(key) or {}
        if prior.get("sha256") == digest and prior.get("intake_exit_code") == 0:
            actions.append({"path": key, "action": "skip", "reason": "already_processed"})
            continue

        stem_tenant = _tenant_from_stem(path.stem)
        if stem_tenant and stem_tenant in INTERNAL_TENANT_STEMS:
            actions.append({"path": key, "action": "skip", "reason": "internal_lane_tenant"})
            continue

        analysis = _analyze_jsonl(path)
        if not analysis["eligible_for_auto_intake"]:
            processed[key] = {
                "sha256": digest,
                "skipped_at_utc": _utc_now(),
                "reason": "not_eligible",
                "analysis": analysis,
            }
            actions.append({"path": key, "action": "skip", "reason": "not_eligible", "analysis": analysis})
            continue

        tenant_id = stem_tenant or _tenant_from_stem(path.stem)
        if not tenant_id:
            actions.append({"path": key, "action": "skip", "reason": "intake_filename_not_tenant_slug"})
            continue

        prov_ok, prov_detail = _provenance_gate_ok(tenant_id, path)
        if not prov_ok:
            if not dry_run:
                processed[key] = {
                    "sha256": digest,
                    "skipped_at_utc": _utc_now(),
                    "reason": "provenance_gate_failed",
                    "detail": prov_detail,
                }
            actions.append(
                {"path": key, "action": "skip", "reason": "provenance_gate_failed", "detail": prov_detail}
            )
            continue

        if dry_run:
            actions.append({"path": key, "action": "would_run_intake", "sha256": digest[:16], "tenant_id": tenant_id})
            continue

        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(AUTO_PS1),
                "-SessionJsonl",
                key,
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        exit_code = proc.returncode
        last_exit = exit_code if exit_code != 0 else last_exit
        processed[key] = {
            "sha256": digest,
            "processed_at_utc": _utc_now(),
            "intake_exit_code": exit_code,
            "analysis": analysis,
        }
        actions.append(
            {
                "path": key,
                "action": "ran_intake",
                "exit_code": exit_code,
                "stdout_tail": (proc.stdout or "")[-500:],
                "stderr_tail": (proc.stderr or "")[-500:],
            }
        )

    state["processed"] = processed
    if not dry_run:
        _save_state(state_path, state)

    return {
        "schema": "wtt_pilot_intake_drop_watch_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "intake_dir": _rel(active_intake),
        "dry_run": dry_run,
        "candidate_count": len(candidates),
        "actions": actions,
        "ok": last_exit == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--state", type=Path, default=STATE_DEFAULT)
    ap.add_argument("--out", type=Path, default=REPORT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-jsonl", type=Path, default=None, help="Process this file even if already seen (re-hash).")
    ap.add_argument("--intake-dir", type=Path, default=None)
    args = ap.parse_args()

    intake_dir = args.intake_dir
    if intake_dir is None:
        env_intake = __import__("os").environ.get("MKM_WTT_INTAKE_DIR", "").strip()
        if env_intake:
            intake_dir = Path(env_intake)

    report = run_watch(
        state_path=args.state,
        dry_run=args.dry_run,
        force_path=args.force_jsonl,
        intake_dir=intake_dir,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "candidates": report["candidate_count"],
                "actions": [a.get("action") for a in report["actions"]],
            }
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
