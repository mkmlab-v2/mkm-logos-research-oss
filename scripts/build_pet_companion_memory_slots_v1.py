#!/usr/bin/env python3
"""Build lightweight pet companion memory slots from coach events in KV."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_JSON = ROOT / "reports" / "pet_companion_memory_slots_latest.json"
DEFAULT_OUT_MD = ROOT / "reports" / "pet_companion_memory_slots_latest.md"
DEFAULT_KV_PREFIX = "pet_companion/coach_events/"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, str, str]:
    if cmd and cmd[0] == "npx":
        npx_path = shutil.which("npx") or shutil.which("npx.cmd")
        if npx_path:
            cmd = [npx_path, *cmd[1:]]
    env = dict(os.environ)
    env.pop("CLOUDFLARE_API_TOKEN", None)
    env.pop("CF_API_TOKEN", None)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _load_rows_from_kv(namespace_id: str, prefix: str, *, wrangler_cwd: Path) -> list[dict]:
    rows: list[dict] = []
    list_cmd = [
        "npx",
        "wrangler",
        "kv",
        "key",
        "list",
        "--namespace-id",
        namespace_id,
        "--prefix",
        prefix,
        "--remote",
    ]
    code, stdout, _stderr = _run(list_cmd, cwd=wrangler_cwd)
    if code != 0:
        return rows
    try:
        keys = json.loads(stdout)
    except json.JSONDecodeError:
        return rows
    if not isinstance(keys, list):
        return rows
    for key in keys:
        if not isinstance(key, dict):
            continue
        name = key.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        get_cmd = [
            "npx",
            "wrangler",
            "kv",
            "key",
            "get",
            "--namespace-id",
            namespace_id,
            name,
            "--remote",
        ]
        get_code, get_stdout, _get_stderr = _run(get_cmd, cwd=wrangler_cwd)
        if get_code != 0:
            continue
        try:
            payload = json.loads(get_stdout)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("schema") == "pet_companion_coach_event_v1":
            rows.append(payload)
    return rows


def _filter_rows(rows: list[dict], days: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    out: list[dict] = []
    for row in rows:
        ts = _parse_ts(str(row.get("ts_utc") or ""))
        if ts and ts >= cutoff:
            out.append(row)
    return out


def _build_slots(profile_id: str, rows: list[dict]) -> list[dict]:
    scenario_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    emergency = 0
    max_question_chars = 0
    last_ts = None
    for row in rows:
        scenario = str(row.get("scenario") or "other")
        status = str(row.get("status") or "unknown")
        scenario_counter[scenario] += 1
        status_counter[status] += 1
        if bool(row.get("emergency_signal")):
            emergency += 1
        qlen = int(row.get("question_chars") or 0)
        max_question_chars = max(max_question_chars, qlen)
        ts_raw = str(row.get("ts_utc") or "")
        if not last_ts or ts_raw > last_ts:
            last_ts = ts_raw

    dominant = scenario_counter.most_common(1)[0][0] if scenario_counter else "other"
    slots = [
        {
            "slot_id": f"{profile_id}:dominant_scenario",
            "type": "behavior_pattern",
            "value": dominant,
            "weight": scenario_counter.get(dominant, 0),
            "keywords": [dominant, "패턴", "반복"],
        },
        {
            "slot_id": f"{profile_id}:safety_posture",
            "type": "safety_posture",
            "value": "abstain_first" if emergency > 0 else "guided_checklist_first",
            "weight": emergency,
            "keywords": ["응급", "위험", "병원", "abstain", "안전"],
        },
        {
            "slot_id": f"{profile_id}:interaction_intensity",
            "type": "interaction_style",
            "value": "detailed" if max_question_chars >= 25 else "brief",
            "weight": max_question_chars,
            "keywords": ["상세", "간단", "요약", "질문길이"],
        },
        {
            "slot_id": f"{profile_id}:status_distribution",
            "type": "status_distribution",
            "value": dict(status_counter),
            "weight": sum(status_counter.values()),
            "keywords": ["guidance", "abstain", "분포", "히스토리"],
        },
    ]
    return [
        {
            **slot,
            "profile_id": profile_id,
            "updated_at_utc": _utc_now(),
            "last_event_ts_utc": last_ts,
            "hypothesis_tier": "B",
            "research_only": True,
            "non_gating": True,
        }
        for slot in slots
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pet companion memory slots from KV events.")
    ap.add_argument("--kv-namespace-id", type=str, default="2dc41cddcb1e417181bd2876916697bd")
    ap.add_argument("--kv-prefix", type=str, default=DEFAULT_KV_PREFIX)
    ap.add_argument("--wrangler-cwd", type=Path, default=ROOT / "projects" / "mkm" / "mkm-life")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    namespace_id = args.kv_namespace_id.strip()
    rows = _load_rows_from_kv(namespace_id, args.kv_prefix, wrangler_cwd=args.wrangler_cwd) if namespace_id else []
    rows = _filter_rows(rows, args.days)

    profile_rows: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        pid = str(row.get("profile_id") or "").strip()
        if not pid:
            continue
        profile_rows[pid].append(row)

    slots_by_profile: dict[str, list[dict]] = {}
    total_slots = 0
    for profile_id, items in sorted(profile_rows.items(), key=lambda x: x[0]):
        slots = _build_slots(profile_id, items)
        slots_by_profile[profile_id] = slots
        total_slots += len(slots)

    doc = {
        "schema": "pet_companion_memory_slots_v1",
        "generated_at_utc": _utc_now(),
        "window_days": max(1, args.days),
        "events_count": len(rows),
        "profiles_count": len(slots_by_profile),
        "slots_count": total_slots,
        "slots_by_profile": slots_by_profile,
        "track_wall": {
            "hypothesis_tier": "B",
            "research_only": True,
            "non_gating": True,
        },
    }

    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)

    if total_slots == 0 and out_json.is_file():
        try:
            prior = json.loads(out_json.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            prior = None
        if isinstance(prior, dict) and int(prior.get("slots_count") or 0) > 0:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "skipped_write": True,
                        "reason": "kv_empty_preserved_prior_slots",
                        "prior_slots_count": prior.get("slots_count"),
                        "out": str(out_json),
                    },
                    ensure_ascii=False,
                )
            )
            print(str(out_md))
            return 0

    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Pet Companion Memory Slots",
        "",
        f"- generated_at_utc: {doc['generated_at_utc']}",
        f"- window_days: {doc['window_days']}",
        f"- events_count: {doc['events_count']}",
        f"- profiles_count: {doc['profiles_count']}",
        f"- slots_count: {doc['slots_count']}",
        "",
        "## Profiles",
        "",
    ]
    for profile_id, slots in slots_by_profile.items():
        md_lines.append(f"- {profile_id}: {len(slots)} slots")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

