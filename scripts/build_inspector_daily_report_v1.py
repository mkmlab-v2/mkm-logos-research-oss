#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "inspector_daily_report_latest.json"
REPORTS = ROOT / "reports"
BTRACK_HIT_BUNDLE = REPORTS / "btrack_btc_weight_hit_rate_bundle_latest.json"
TASK_BTRACK_WEEKLY = "MKM-BTrack-BtcWeight-HitRateBundle-Weekly"
TASK_KM_CDS_BATCH_WEEKLY = "MKM-KmPhysician-CdsEnvelopeBatch-Weekly"
KM_PHYSICIAN_CDS_SCHEMA = ROOT / "docs" / "final" / "schemas" / "km_physician_cds_assist_envelope_v1.schema.json"
KM_PHYSICIAN_CDS_BUILDER = ROOT / "scripts" / "build_km_physician_cds_assist_envelope_v1.py"
KM_PHYSICIAN_CDS_BATCH = ROOT / "scripts" / "run_km_physician_cds_assist_envelope_batch_v1.py"
KM_PHYSICIAN_CDS_BATCH_ARTIFACT = REPORTS / "km_physician_cds_envelope_batch_latest.jsonl"
AUTOMATION_REGISTRY_JSON = (
    ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal" / "automation_registry.json"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _task_status(task_name: str) -> dict[str, Any]:
    ps = (
        f"$i=Get-ScheduledTaskInfo -TaskName '{task_name}' -ErrorAction SilentlyContinue; "
        "if($i){"
        "Write-Output ($i.LastTaskResult);"
        "} else { Write-Output 'MISSING' }"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    val = (proc.stdout or "").strip()
    if val == "MISSING" or not val:
        return {"task_name": task_name, "state": "unknown", "last_task_result": None}
    try:
        code = int(val)
    except ValueError:
        return {"task_name": task_name, "state": "unknown", "last_task_result": None}
    return {
        "task_name": task_name,
        "state": "ok" if code == 0 else "fail",
        "last_task_result": code,
    }


def _repo_file_signal(path: Path) -> dict[str, Any]:
    """Fact-Lock SSOT path presence (non-gating observation)."""
    try:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel = str(path)
    return {"artifact": rel, "state": "ok" if path.is_file() else "missing"}


def _optional_jsonl_artifact_signal(path: Path, *, stale_days: int = 21) -> dict[str, Any]:
    """Optional batch output: missing is ok; if present, surface age vs stale_days (non-gating)."""
    try:
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel = str(path)
    if not path.is_file():
        return {"artifact": rel, "state": "absent", "stale_warning": False}

    try:
        mtime = path.stat().st_mtime
        age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400.0
        stale = age_days >= float(stale_days)
    except OSError:
        stale = False

    return {"artifact": rel, "state": "ok", "stale_warning": stale}


def _bundle_report_signal(bundle_path: Path, *, stale_days: int = 10) -> dict[str, Any]:
    """B-track BTC hit-rate bundle (research): presence + optional staleness vs weekly cadence."""
    doc = _read_json(bundle_path)
    try:
        rel = str(bundle_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel = str(bundle_path)
    if not doc:
        return {"artifact": rel, "state": "missing", "stale_warning": False}

    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    ts = doc.get("generated_at_utc")
    stale = False
    if isinstance(ts, str) and ts.strip():
        try:
            tsi = ts.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(tsi)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
            stale = age.days >= stale_days
        except (ValueError, TypeError, OSError):
            stale = False

    return {
        "artifact": rel,
        "state": "ok",
        "generated_at_utc": ts if isinstance(ts, str) else None,
        "winner_profile": summary.get("winner_profile"),
        "stale_warning": stale,
        "schema": doc.get("schema"),
    }


def _domain_status(runtime_ok: bool, cost_ok: bool, security_ok: bool, quality_ok: bool) -> tuple[str, int]:
    score = 100
    if not runtime_ok:
        score -= 25
    if not cost_ok:
        score -= 20
    if not security_ok:
        score -= 30
    if not quality_ok:
        score -= 15
    if score >= 80:
        return "GREEN", score
    if score >= 60:
        return "YELLOW", score
    return "RED", score


def main() -> int:
    c2 = _read_json(ART / "c2_aegis_guardrail_status_latest.json")
    cost = _read_json(ART / "cost_watch_monitor_latest.json")
    go = _read_json(ART / "a_track_go_nogo_status_latest.json")

    t_daily = _task_status("GeneralProphecyDailyQueueV1")
    t_vibe = _task_status("VibeDailyProphecyEvolutionLoop")
    t_btrack_weekly = _task_status(TASK_BTRACK_WEEKLY)
    t_km_cds_weekly = _task_status(TASK_KM_CDS_BATCH_WEEKLY)
    bundle_sig = _bundle_report_signal(BTRACK_HIT_BUNDLE)
    cds_batch_sig = _optional_jsonl_artifact_signal(KM_PHYSICIAN_CDS_BATCH_ARTIFACT)

    runtime_ok = all(
        x.get("state") == "ok"
        for x in (t_daily, t_vibe, t_btrack_weekly, t_km_cds_weekly)
        if x.get("last_task_result") is not None
    )
    cost_ok = bool(cost) and str((cost.get("billing") or {}).get("status") or "") == "ok"
    security_ok = str(c2.get("status") or "").startswith("GREEN")
    quality_ok = str((go.get("result") or {}).get("overall_go_no_go") or "") == "GO"

    overall, score = _domain_status(runtime_ok, cost_ok, security_ok, quality_ok)

    # NON_GATING affect layer: used to shape wording and proposals only (never triggers actions).
    calm = 0.7 if runtime_ok and security_ok else 0.4
    urgency = 0.2 if runtime_ok else 0.6
    fatigue = 0.3
    confidence = 0.7 if overall == "GREEN" else 0.5
    tone = "Keep it concise; focus on highest-signal changes only."
    opx = "Low friction expected; monitor quietly unless failures repeat."
    style = "summary_first"
    report: dict[str, Any] = {
        "schema": "inspector_daily_report_v1",
        "schema_version": "1.0.0",
        "ts_utc": _now_iso(),
        "fact_lock": {
            "constitution_ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
            "mode": "observation_only_2weeks",
        },
        "system_posture": {"overall": overall, "score_0_100": score},
        "affect_layer": {
            "non_gating": True,
            "mood_vector": {"calm": calm, "urgency": urgency, "fatigue": fatigue, "confidence": confidence},
            "tone_suggestion": tone,
            "operator_experience": opx,
            "recommendation_style": style,
        },
        "human_feedback_slot": {
            "enabled": True,
            "prompt": "Was this report helpful? (e.g. ok / too noisy / missed X / great).",
            "response": "",
        },
        "domains": {
            "runtime_health": {
                "status": "GREEN" if runtime_ok else "YELLOW",
                "signals": [t_daily, t_vibe, t_btrack_weekly, t_km_cds_weekly, bundle_sig],
            },
            "cost_governance": {
                "status": "GREEN" if cost_ok else "YELLOW",
                "signals": [{"billing_status": (cost.get("billing") or {}).get("status")}],
            },
            "security_ip": {
                "status": "GREEN" if security_ok else "YELLOW",
                "signals": [{"c2_aegis_status": c2.get("status")}],
            },
            "code_quality_env": {
                "status": "GREEN" if quality_ok else "YELLOW",
                "signals": [
                    {"a_track_go_no_go": (go.get("result") or {}).get("overall_go_no_go")},
                    _repo_file_signal(KM_PHYSICIAN_CDS_SCHEMA),
                    _repo_file_signal(KM_PHYSICIAN_CDS_BUILDER),
                    _repo_file_signal(KM_PHYSICIAN_CDS_BATCH),
                    cds_batch_sig,
                    _repo_file_signal(AUTOMATION_REGISTRY_JSON),
                ],
            },
        },
        "source_evidence": {
            "c2_aegis": "docs/final/artifacts/c2_aegis_guardrail_status_latest.json",
            "cost_watch": "docs/final/artifacts/cost_watch_monitor_latest.json",
            "a_track_go_nogo": "docs/final/artifacts/a_track_go_nogo_status_latest.json",
            "btrack_btc_weight_hit_rate_bundle": "reports/btrack_btc_weight_hit_rate_bundle_latest.json",
            "km_physician_cds_schema": "docs/final/schemas/km_physician_cds_assist_envelope_v1.schema.json",
            "km_physician_cds_builder": "scripts/build_km_physician_cds_assist_envelope_v1.py",
            "km_physician_cds_batch_runner": "scripts/run_km_physician_cds_assist_envelope_batch_v1.py",
            "km_physician_cds_envelope_batch_artifact": "reports/km_physician_cds_envelope_batch_latest.jsonl",
            "automation_registry_json": "projects/bitcoin-trading/ops/windows-rehearsal/automation_registry.json",
        },
        "actions_proposed": [],
        "audit": {"run_id": str(uuid.uuid4()), "agent": "MKM_Internal_Inspector_v1", "publish_scope": "local_only"},
    }

    if not runtime_ok:
        report["actions_proposed"].append(
            {
                "action_id": "act-runtime-retry-001",
                "level": "L1",
                "owner": "Operator",
                "description": "retry failed scheduled task once",
                "requires_commander_approval": False,
            }
        )

    if bundle_sig.get("state") == "ok" and bundle_sig.get("stale_warning"):
        report["actions_proposed"].append(
            {
                "action_id": "act-btrack-bundle-stale-001",
                "level": "L2",
                "owner": "Operator",
                "description": "run scripts/run_btc_weight_hit_rate_bundle_v1.py or verify MKM-BTrack-BtcWeight-HitRateBundle-Weekly last run",
                "requires_commander_approval": False,
            }
        )

    if cds_batch_sig.get("state") == "ok" and cds_batch_sig.get("stale_warning"):
        report["actions_proposed"].append(
            {
                "action_id": "act-km-physician-cds-batch-stale-001",
                "level": "L2",
                "owner": "Operator",
                "description": (
                    "refresh reports/km_physician_cds_envelope_batch_latest.jsonl via "
                    "scripts/run_km_physician_cds_assist_envelope_batch_v1.py "
                    "(input example: tests/fixtures/km_physician_cds_assist_payload_batch_v1.example.jsonl)"
                ),
                "requires_commander_approval": False,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {OUT}")
    print(f"overall: {overall} score={score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

