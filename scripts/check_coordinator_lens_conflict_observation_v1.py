#!/usr/bin/env python3
"""O-P22: Observe 3-lens fusion conflicts / market_sasang veto — info webhook only (B-track).

Does not modify prophecy score, todo_queue, or live trading paths.
Infrastructure failures (missing stub, bad schema) exit 1; semantic conflict/veto exit 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUB = Path("docs/final/artifacts/independent_lens_fusion_stub_latest.json")
DEFAULT_OUT = Path("reports/coordinator_lens_conflict_observation_latest.json")
DEFAULT_DEDUP_STATE = Path("reports/coordinator_lens_conflict_dedup_state_v1.json")
NARRATIVE_CLIP = 400
EXPECTED_STUB_SCHEMA = "independent_lens_fusion_stub_v0"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.strptime(ts.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _market_sasang_veto(inputs: list[Any]) -> tuple[bool, list[str]]:
    for row in inputs:
        if not isinstance(row, dict) or row.get("lens_id") != "market_sasang":
            continue
        block = row.get("market_sasang_lens_v1")
        if not isinstance(block, dict):
            return False, []
        codes = block.get("veto_reason_codes")
        reason_codes = [str(c) for c in codes] if isinstance(codes, list) else []
        return bool(block.get("veto_force_hold")), reason_codes
    return False, []


def _stale_lens_ids(inputs: list[Any], now: datetime, max_age: timedelta) -> list[str]:
    stale: list[str] = []
    for row in inputs:
        if not isinstance(row, dict):
            continue
        lens_id = str(row.get("lens_id") or "")
        if not lens_id:
            continue
        ts = _parse_utc(str(row.get("artifact_ts_utc") or ""))
        if ts is None or (now - ts) > max_age:
            stale.append(lens_id)
    return stale


def _alert_fingerprint(
    majority_sign: str,
    minority_ids: list[str],
    verse_ids: list[str],
    veto_active: bool,
    veto_codes: list[str],
) -> str:
    minority_s = "-".join(sorted(minority_ids))
    verse_s = "-".join(sorted(verse_ids))
    veto_codes_s = "-".join(sorted(veto_codes))
    raw = f"{majority_sign}|{minority_s}|{verse_s}|veto={int(veto_active)}|{veto_codes_s}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _load_dedup_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = _load_json(path)
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _dedup_allows(fingerprint: str, state: dict[str, Any], now: datetime, window: timedelta) -> bool:
    if state.get("last_fingerprint") != fingerprint:
        return True
    last_utc = _parse_utc(str(state.get("last_fired_utc") or ""))
    if last_utc is None:
        return True
    return (now - last_utc) >= window


def _resolve_webhook(skip: bool) -> str:
    if skip:
        return ""
    truthy = {"1", "true", "yes", "on"}
    if (os.getenv("MKM_COORD_CONFLICT_SKIP_WEBHOOK") or "").strip().lower() in truthy:
        return ""
    return (os.getenv("MKM_COORD_CONFLICT_WEBHOOK_URL") or os.getenv("OPS_ALARM_WEBHOOK_URL") or "").strip()


def _post_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    req = request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            code = int(getattr(resp, "status", 0) or 0)
            return 200 <= code < 300, f"http_status={code}"
    except error.HTTPError as exc:
        return False, f"http_error_{exc.code}"
    except error.URLError as exc:
        return False, f"url_error_{exc.reason}"
    except OSError as exc:
        return False, str(exc)


def _validate_stub(doc: dict[str, Any]) -> str | None:
    if doc.get("schema") != EXPECTED_STUB_SCHEMA:
        return f"schema must be {EXPECTED_STUB_SCHEMA}"
    if doc.get("mode") != "observation_only":
        return "mode must be observation_only"
    if not isinstance(doc.get("inputs"), list) or len(doc.get("inputs") or []) < 3:
        return "inputs must be array with >= 3 items"
    if not isinstance(doc.get("consensus"), dict):
        return "consensus object required"
    if not isinstance(doc.get("conflict_summary"), dict):
        return "conflict_summary object required"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--fusion-stub-json", type=Path, default=DEFAULT_STUB)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dedup-state-json", type=Path, default=DEFAULT_DEDUP_STATE)
    ap.add_argument("--max-age-hours", type=float, default=36.0)
    ap.add_argument("--dedup-hours", type=float, default=24.0)
    ap.add_argument("--skip-webhook", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    stub_path = args.fusion_stub_json if args.fusion_stub_json.is_absolute() else root / args.fusion_stub_json
    out_path = args.out_json if args.out_json.is_absolute() else root / args.out_json
    dedup_path = args.dedup_state_json if args.dedup_state_json.is_absolute() else root / args.dedup_state_json

    now = datetime.now(timezone.utc)
    generated = _iso_now()
    max_age = timedelta(hours=float(args.max_age_hours))
    dedup_window = timedelta(hours=float(args.dedup_hours))

    base: dict[str, Any] = {
        "schema": "coordinator_lens_conflict_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": generated,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "observation_only": True,
        "fusion_stub_path": str(stub_path),
        "exit_semantics": "semantic_observation_always_exit_0_unless_infra",
    }

    if not stub_path.is_file():
        print(f"[FATAL] Missing fusion stub: {stub_path}")
        return 1

    try:
        stub = _load_json(stub_path)
    except json.JSONDecodeError as exc:
        print(f"[FATAL] Invalid JSON in fusion stub: {exc}")
        return 1

    err = _validate_stub(stub)
    if err:
        print(f"[FATAL] Fusion stub validation failed: {err}")
        return 1

    stub_ts = _parse_utc(str(stub.get("ts_utc") or ""))
    if stub_ts is None:
        print("[FATAL] Invalid or missing ts_utc on fusion stub")
        return 1

    inputs = stub.get("inputs") or []
    consensus = stub.get("consensus") or {}
    conflict_summary = stub.get("conflict_summary") or {}
    conflict_count = int(consensus.get("conflict_count") or 0)
    veto_active, veto_codes = _market_sasang_veto(inputs)
    stale_lens = _stale_lens_ids(inputs, now, max_age)
    stub_stale = (now - stub_ts) > max_age

    base["fusion_stub_ts_utc"] = stub.get("ts_utc")
    base["consensus"] = {
        "conflict_count": conflict_count,
        "agreement_rate": consensus.get("agreement_rate"),
        "consensus_sign": consensus.get("consensus_sign"),
    }
    base["market_sasang_veto"] = {
        "veto_force_hold": veto_active,
        "veto_reason_codes": veto_codes,
    }

    if stub_stale or stale_lens:
        base["status"] = "STALE"
        base["stale_inputs"] = True
        base["stale_stub_top_level"] = stub_stale
        base["stale_lens_ids"] = stale_lens
        base["webhook"] = {"status": "skipped_stale_inputs"}
        _write_json(out_path, base)
        print(f"WROTE: {out_path} status=STALE stale_lens={stale_lens}")
        return 0

    trigger = conflict_count >= 1 or veto_active
    if not trigger:
        base["status"] = "CONSENSUS"
        base["conflict_active"] = False
        base["webhook"] = {"status": "skipped_no_trigger"}
        _write_json(out_path, base)
        print(f"WROTE: {out_path} status=CONSENSUS")
        return 0

    majority_sign = str(conflict_summary.get("majority_sign") or consensus.get("consensus_sign") or "unknown")
    minority_ids = [str(x) for x in (conflict_summary.get("minority_lens_ids") or []) if x]
    verse_ids = [str(x) for x in (conflict_summary.get("logos_evidence_verse_ids") or []) if x]
    narrative = str(conflict_summary.get("conflict_narrative_guarded") or "")
    fingerprint = _alert_fingerprint(majority_sign, minority_ids, verse_ids, veto_active, veto_codes)

    base["status"] = "CONFLICT_OBSERVED"
    base["conflict_active"] = conflict_count >= 1
    base["veto_active"] = veto_active
    base["alert_fingerprint"] = fingerprint
    base["conflict_summary_clip"] = narrative[:NARRATIVE_CLIP]

    dedup_state = _load_dedup_state(dedup_path)
    allow_fire = _dedup_allows(fingerprint, dedup_state, now, dedup_window)
    webhook_url = _resolve_webhook(args.skip_webhook)

    webhook_block: dict[str, Any] = {
        "status": "skipped_dedup_guard",
        "fingerprint": fingerprint,
        "configured": bool(webhook_url),
    }

    if allow_fire and webhook_url:
        payload = {
            "event": "coordinator_lens_conflict_observation_v1",
            "grade": "MKM_COORD_CONFLICT_WARN",
            "generated_at_utc": generated,
            "hypothesis_tier": "B",
            "research_only": True,
            "observation_only": True,
            "conflict_count": conflict_count,
            "veto_force_hold": veto_active,
            "veto_reason_codes": veto_codes,
            "majority_sign": majority_sign,
            "minority_lens_ids": minority_ids,
            "logos_evidence_verse_ids": verse_ids,
            "conflict_narrative_guarded": narrative[:NARRATIVE_CLIP],
            "fusion_stub_path": str(stub_path),
            "alert_fingerprint": fingerprint,
        }
        ok, detail = _post_webhook(webhook_url, payload)
        webhook_block["status"] = "posted" if ok else f"failed:{detail}"
        webhook_block["post_ok"] = ok
        webhook_block["detail"] = detail
        if ok:
            dedup_state = {
                "schema": "coordinator_lens_conflict_dedup_state_v1",
                "last_fingerprint": fingerprint,
                "last_fired_utc": generated,
                "last_status": "ALERT_FIRED",
            }
            _write_json(dedup_path, dedup_state)
            base["status"] = "ALERT_FIRED"
    elif allow_fire and not webhook_url:
        webhook_block["status"] = "skipped_no_webhook"
        base["status"] = "CONFLICT_NO_WEBHOOK"
    else:
        base["status"] = "CONFLICT_DUPLICATE_GUARDED"

    base["webhook"] = webhook_block
    _write_json(out_path, base)
    print(f"WROTE: {out_path} status={base['status']} webhook={webhook_block.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
