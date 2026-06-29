#!/usr/bin/env python3
"""Resolve WTT pilot tenant_id + session JSONL for auto intake ([HYPO])."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTAKE_DIR = ROOT / "data/wtt/intake"
DEFAULT_CONFIG = ROOT / "docs/final/artifacts/wtt_pilot_active_tenant_v1_latest.json"
DEFAULT_TENANT = "wtt-customer-live-v1"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,48}[a-z0-9]$")
BOOTSTRAP_PREFIX = "wtt_pilot_"
SKIP_LABELS = frozenset({"pilot_fill_template", "synthetic_spicy", "synthetic_stub"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _is_eligible_intake_file(path: Path, *, allow_fill_template: bool) -> tuple[bool, str]:
    if not path.name.endswith(".jsonl"):
        return False, "not_jsonl"
    if path.name.startswith(BOOTSTRAP_PREFIX):
        return False, "bootstrap_copy"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            labels = set(row.get("labels") or [])
            if not allow_fill_template and labels & SKIP_LABELS:
                return False, f"skip_labels:{','.join(sorted(labels & SKIP_LABELS))}"
            return True, "ok"
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"read_error:{exc}"
    return False, "empty"


def _list_candidates(*, allow_fill_template: bool) -> list[Path]:
    if not INTAKE_DIR.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(INTAKE_DIR.glob("*.jsonl")):
        ok, _ = _is_eligible_intake_file(path, allow_fill_template=allow_fill_template)
        if ok:
            out.append(path.resolve())
    return out


def _tenant_from_stem(stem: str) -> str | None:
    if SLUG_RE.match(stem):
        return stem
    return None


def resolve_target(
    *,
    config_path: Path,
    session_override: Path | None,
    tenant_override: str | None,
    prefer_newest: bool,
    allow_fill_template: bool,
) -> dict[str, Any]:
    cfg = _load_config(config_path)
    cfg_tenant = (tenant_override or cfg.get("tenant_id") or os.environ.get("MKM_WTT_PILOT_TENANT_ID") or "").strip()
    cfg_session = cfg.get("session_jsonl")

    session_path: Path | None = None
    resolution = "unresolved"
    candidates = _list_candidates(allow_fill_template=allow_fill_template)

    explicit_tenant = bool(tenant_override)

    if session_override is not None:
        session_path = session_override.resolve()
        if not session_path.is_file():
            return {
                "ok": False,
                "error": f"session_jsonl not found: {_rel(session_path)}",
                "candidates": [_rel(p) for p in candidates],
            }
        ok, reason = _is_eligible_intake_file(session_path, allow_fill_template=allow_fill_template)
        if not ok:
            return {
                "ok": False,
                "error": f"session not eligible: {reason}",
                "session_jsonl": _rel(session_path),
            }
        stem_tenant = _tenant_from_stem(session_path.stem)
        if explicit_tenant:
            tenant_id = tenant_override  # type: ignore[assignment]
            resolution = "session_override+cli_tenant"
        elif stem_tenant:
            tenant_id = stem_tenant
            resolution = "session_override+filename_stem"
        elif cfg_tenant:
            tenant_id = cfg_tenant
            resolution = "session_override+config_tenant"
        else:
            tenant_id = DEFAULT_TENANT
            resolution = "session_override+default_tenant"
    elif cfg_session:
        session_path = (ROOT / cfg_session).resolve() if not Path(cfg_session).is_absolute() else Path(cfg_session).resolve()
        if not session_path.is_file():
            return {"ok": False, "error": f"config session missing: {cfg_session}"}
        stem_tenant = _tenant_from_stem(session_path.stem)
        if explicit_tenant:
            tenant_id = tenant_override  # type: ignore[assignment]
        elif cfg_tenant:
            tenant_id = cfg_tenant
        elif stem_tenant:
            tenant_id = stem_tenant
        else:
            tenant_id = DEFAULT_TENANT
        resolution = "config_session"
    elif len(candidates) == 1:
        session_path = candidates[0]
        stem_tenant = _tenant_from_stem(session_path.stem)
        if explicit_tenant:
            tenant_id = tenant_override  # type: ignore[assignment]
            resolution = "single_intake_file+cli_tenant"
        elif stem_tenant:
            tenant_id = stem_tenant
            resolution = "single_intake_file+filename_stem"
        elif cfg_tenant:
            tenant_id = cfg_tenant
            resolution = "single_intake_file+config_tenant"
        else:
            tenant_id = DEFAULT_TENANT
            resolution = "single_intake_file+default_tenant"
    elif len(candidates) == 0:
        return {
            "ok": False,
            "error": "no eligible JSONL in data/wtt/intake/ (drop <tenant>-wtt-pilot-v1.jsonl or set wtt_pilot_active_tenant_v1_latest.json)",
            "intake_dir": _rel(INTAKE_DIR),
            "hint": f"default tenant if file stem matches slug: {DEFAULT_TENANT}",
        }
    elif prefer_newest:
        session_path = max(candidates, key=lambda p: p.stat().st_mtime)
        stem_tenant = _tenant_from_stem(session_path.stem)
        if explicit_tenant:
            tenant_id = tenant_override  # type: ignore[assignment]
        elif stem_tenant:
            tenant_id = stem_tenant
            resolution = "prefer_newest+filename_stem"
        elif cfg_tenant:
            tenant_id = cfg_tenant
            resolution = "prefer_newest+config_tenant"
        else:
            tenant_id = DEFAULT_TENANT
            resolution = "prefer_newest+default_tenant"
    else:
        return {
            "ok": False,
            "error": "ambiguous: multiple intake JSONL files; set session_jsonl in config or use --prefer-newest",
            "candidates": [_rel(p) for p in candidates],
        }

    if not SLUG_RE.match(tenant_id):
        return {
            "ok": False,
            "error": f"invalid tenant_id slug: {tenant_id!r}",
            "pattern": SLUG_RE.pattern,
        }

    return {
        "ok": True,
        "tenant_id": tenant_id,
        "session_jsonl": _rel(session_path),  # type: ignore[arg-type]
        "resolution": resolution,
        "default_tenant_fallback": DEFAULT_TENANT,
        "candidates": [_rel(p) for p in candidates],
        "send_gate": "HOLD",
        "research_only": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--session-jsonl", type=Path, default=None)
    ap.add_argument("--tenant-id", type=str, default=None)
    ap.add_argument("--prefer-newest", action="store_true")
    ap.add_argument("--allow-fill-template", action="store_true")
    ap.add_argument("--write-config", action="store_true", help="Persist resolved tenant+session to active tenant JSON.")
    ap.add_argument("--out", type=Path, default=ROOT / "reports/wtt_pilot_intake_resolve_v1_latest.json")
    args = ap.parse_args()

    result = resolve_target(
        config_path=args.config,
        session_override=args.session_jsonl,
        tenant_override=(args.tenant_id or "").strip() or None,
        prefer_newest=args.prefer_newest,
        allow_fill_template=args.allow_fill_template,
    )
    result["schema"] = "wtt_pilot_intake_resolve_v1"
    result["generated_at_utc"] = _utc_now()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_config and result.get("ok"):
        payload = {
            "schema": "wtt_pilot_active_tenant_v1",
            "updated_at_utc": _utc_now(),
            "tenant_id": result["tenant_id"],
            "session_jsonl": result["session_jsonl"],
            "note_ko": "session_jsonl 고정 또는 null 시 intake 폴더 자동 탐색",
        }
        args.config.parent.mkdir(parents=True, exist_ok=True)
        args.config.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": result.get("ok"), "tenant_id": result.get("tenant_id"), "session_jsonl": result.get("session_jsonl")}))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
