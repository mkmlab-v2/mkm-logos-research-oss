#!/usr/bin/env python3
"""Resolve target WAV paths — local file, delegation sidecar, known case, or OSS fetch [HYPO]."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from scripts.ko_shorts_alignment_routing_lib_v1 import parse_domain_hint_from_filename_v1

ROOT = Path(__file__).resolve().parents[1]

CASE_TO_FETCH_MEMBER: dict[str, str] = {
    "web_pansori": "pansori",
    "web_deeply": "deeply",
    "web_youtube_edu": "youtube_edu",
}

DEFAULT_AUTO_CASE = "web_pansori"
CLINICAL_SIM_CASES = tuple(CASE_TO_FETCH_MEMBER.keys())

DELEGATION_SIDECAR = ROOT / "reports/ko_shorts_target_wav_delegation_v1_latest.json"
INBOX_FIXED_WAV = ROOT / "reports/audio/ko_shorts_target_inbox_v1.wav"
INBOX_DIR = ROOT / "reports/audio/inbox"
ENV_DELEGATED_WAV = "MKM_KO_SHORTS_TARGET_WAV"
DEFAULT_DELEGATE_CASE_ID = "target_custom_v1"


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "custom"


def artifact_paths_for_case_v1(case_id: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "spike_json": f"reports/ko_shorts_stt_timing_{case_id}_v1_latest.json",
        "spike_srt": f"reports/ko_shorts_stt_timing_{case_id}_v1_latest.srt",
        "ass": f"reports/ko_shorts_burnin_{case_id}_v1_latest.ass",
        "srt": f"reports/ko_shorts_burnin_{case_id}_v1_latest.srt",
        "mp4": f"reports/ko_shorts_burnin_{case_id}_v1_latest.mp4",
        "burnin_meta": f"reports/ko_shorts_burnin_{case_id}_v1_latest.json",
    }


def qa_case_dict_from_artifacts(artifacts: dict[str, str]) -> dict[str, str]:
    return {
        "case_id": artifacts["case_id"],
        "spike_json": artifacts["spike_json"],
        "mp4": artifacts["mp4"],
        "srt": artifacts["srt"],
        "ass": artifacts["ass"],
    }


def ensure_fetch_member_wav_v1(member_key: str, *, refetch_missing: bool = True) -> Path:
    from scripts.fetch_ko_shorts_web_speech_wav_v1 import _member_wav_path, fetch_member_source

    wav_path = _member_wav_path(member_key)
    if wav_path is None:
        raise ValueError(f"unknown fetch member: {member_key}")
    if not wav_path.is_file() or refetch_missing:
        fetch_member_source(member_key)
    if not wav_path.is_file():
        raise FileNotFoundError(f"fetch failed for member={member_key}")
    return wav_path


def ensure_wav_for_known_case_v1(case_id: str, *, refetch_missing: bool = True) -> Path:
    member = CASE_TO_FETCH_MEMBER.get(case_id)
    if not member:
        raise ValueError(f"unknown known case_id: {case_id}")
    return ensure_fetch_member_wav_v1(member, refetch_missing=refetch_missing)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_delegation_sidecar_v1(path: Path | None = None) -> dict[str, Any]:
    sidecar_path = path or DELEGATION_SIDECAR
    if not sidecar_path.is_file():
        return {}
    doc = _read_json(sidecar_path)
    return doc if isinstance(doc, dict) else {}


def _path_if_file(raw: str | Path) -> Path | None:
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return p if p.is_file() else None


def discover_delegated_wav_v1(
    *,
    sidecar: dict[str, Any] | None = None,
    sidecar_path: Path | None = None,
) -> dict[str, Any] | None:
    """
    Commander delegation — no CLI --wav required.

    Priority:
    1. sidecar `wav` / `wav_path` (if enabled != false)
    2. env MKM_KO_SHORTS_TARGET_WAV
    3. reports/audio/ko_shorts_target_inbox_v1.wav
    4. newest *.wav in reports/audio/inbox/
    """
    sc = sidecar if sidecar is not None else load_delegation_sidecar_v1(sidecar_path)
    if sc.get("enabled") is False:
        return None

    case_id = sc.get("case_id") or DEFAULT_DELEGATE_CASE_ID
    domain_hint = sc.get("domain_hint")

    for key in ("wav", "wav_path"):
        raw = sc.get(key)
        if raw:
            found = _path_if_file(raw)
            if found:
                return {
                    "wav": found,
                    "wav_rel": _rel(found),
                    "case_id": case_id,
                    "domain_hint": domain_hint,
                    "wav_resolved_via": "delegation_sidecar",
                    "delegation_source": key,
                }

    env_raw = os.environ.get(ENV_DELEGATED_WAV, "").strip()
    if env_raw:
        found = _path_if_file(env_raw)
        if found:
            return {
                "wav": found,
                "wav_rel": _rel(found),
                "case_id": case_id,
                "domain_hint": domain_hint,
                "wav_resolved_via": "delegation_env",
                "delegation_source": ENV_DELEGATED_WAV,
            }

    if INBOX_FIXED_WAV.is_file():
        return {
            "wav": INBOX_FIXED_WAV,
            "wav_rel": _rel(INBOX_FIXED_WAV),
            "case_id": case_id,
            "domain_hint": domain_hint,
            "wav_resolved_via": "delegation_inbox_fixed",
            "delegation_source": str(INBOX_FIXED_WAV.relative_to(ROOT)).replace("\\", "/"),
        }

    if INBOX_DIR.is_dir():
        candidates = sorted(
            (p for p in INBOX_DIR.glob("*.wav") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            found = candidates[0]
            return {
                "wav": found,
                "wav_rel": _rel(found),
                "case_id": case_id,
                "domain_hint": domain_hint,
                "wav_resolved_via": "delegation_inbox_newest",
                "delegation_source": _rel(found),
            }

    return None


def resolve_target_wav_v1(
    *,
    wav: Path | str | None = None,
    case_id: str | None = None,
    auto: bool = True,
    refetch_missing: bool = True,
    domain_hint: str | None = None,
    delegate: bool = False,
    delegation_sidecar: Path | None = None,
) -> dict[str, Any]:
    """
    Resolve WAV without user hand-placement when possible.

    Priority:
    1. Explicit wav path (must exist unless case_id maps to fetch member)
    2. delegate=True -> delegation sidecar / env / inbox
    3. Known case_id -> OSS fetch if missing
    4. auto=True -> web_pansori (hardest proxy) with fetch if missing
    """
    resolved_via = "explicit_path"
    hint = domain_hint

    if delegate and not wav:
        delegated = discover_delegated_wav_v1(sidecar_path=delegation_sidecar)
        if delegated:
            wav_path = delegated["wav"]
            cid = case_id or delegated["case_id"]
            artifacts = artifact_paths_for_case_v1(cid)
            if not hint:
                hint = delegated.get("domain_hint") or parse_domain_hint_from_filename_v1(wav_path.name)
            return {
                "ok": True,
                "case_id": cid,
                "wav": wav_path,
                "wav_rel": delegated["wav_rel"],
                "artifacts": artifacts,
                "domain_hint": hint,
                "wav_resolved_via": delegated["wav_resolved_via"],
                "delegation_source": delegated.get("delegation_source"),
                "known_case": False,
            }
        if not auto and not case_id:
            raise FileNotFoundError(
                "delegation empty: set reports/ko_shorts_target_wav_delegation_v1_latest.json "
                f"or drop WAV at {INBOX_FIXED_WAV.name} or reports/audio/inbox/"
            )

    if wav:
        wav_path = Path(wav)
        if not wav_path.is_absolute():
            wav_path = ROOT / wav_path
        if not wav_path.is_file():
            if case_id and case_id in CASE_TO_FETCH_MEMBER:
                wav_path = ensure_wav_for_known_case_v1(case_id, refetch_missing=refetch_missing)
                resolved_via = "auto_fetch_case"
            else:
                raise FileNotFoundError(str(wav_path))
        cid = case_id or f"target_{_slugify(wav_path.stem)}"
        artifacts = artifact_paths_for_case_v1(cid)
        if not hint:
            hint = parse_domain_hint_from_filename_v1(wav_path.name)
        return {
            "ok": True,
            "case_id": cid,
            "wav": wav_path,
            "wav_rel": _rel(wav_path),
            "artifacts": artifacts,
            "domain_hint": hint,
            "wav_resolved_via": resolved_via,
            "known_case": cid in CASE_TO_FETCH_MEMBER,
        }

    cid = case_id or (DEFAULT_AUTO_CASE if auto else "")
    if not cid:
        raise ValueError("provide --wav, --case-id, or --auto")

    if cid in CASE_TO_FETCH_MEMBER:
        wav_path = ensure_wav_for_known_case_v1(cid, refetch_missing=refetch_missing)
        resolved_via = "auto_fetch_case" if auto and not case_id else "known_case_fetch"
    else:
        raise ValueError(f"case_id {cid} requires --wav or a known clinical_sim case")

    artifacts = artifact_paths_for_case_v1(cid)
    if not hint and cid == "web_pansori":
        hint = "traditional_vocal"
    return {
        "ok": True,
        "case_id": cid,
        "wav": wav_path,
        "wav_rel": _rel(wav_path),
        "artifacts": artifacts,
        "domain_hint": hint,
        "wav_resolved_via": resolved_via,
        "known_case": True,
    }
