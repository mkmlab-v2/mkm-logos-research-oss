#!/usr/bin/env python3
"""Discover clinic LOI Figma file by name across team projects.

Writes reports/clinic_loi_figma_discover_v1_latest.json
Updates docs/final/artifacts/clinic_loi_figma_design_ssot_v1_latest.json when found.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SSOT = ROOT / "docs/final/artifacts/clinic_loi_figma_design_ssot_v1_latest.json"
PD_SSOT = ROOT / "docs/final/artifacts/personadiary_figma_design_ssot_v1_latest.json"
OUT = ROOT / "reports/clinic_loi_figma_discover_v1_latest.json"
DEFAULT_TEAM = "1342307617365175074"
TARGET_NAMES = ("mkm-20260624", "MKM-20260624", "mkm 20260624", "Clinic LOI")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_value(name: str) -> str | None:
    import os

    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            if k.strip() == name:
                val = v.strip().strip('"').strip("'")
                if val:
                    return val
    val = os.environ.get(name, "").strip()
    return val or None


def _figma_token() -> str | None:
    return _env_value("MKM_FIGMA_ACCESS_TOKEN") or _env_value("FIGMA_ACCESS_TOKEN")


def _team_id() -> str:
    env_team = _env_value("MKM_FIGMA_TEAM_ID")
    if env_team:
        return env_team.replace("team::", "").strip()
    if PD_SSOT.is_file():
        doc = json.loads(PD_SSOT.read_text(encoding="utf-8-sig"))
        pk = str(doc.get("figma_plan_key") or "")
        if pk.startswith("team::"):
            return pk.split("::", 1)[1]
    return DEFAULT_TEAM


def _api_get(path: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"https://api.figma.com{path}",
        headers={"X-Figma-Token": token},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def discover(token: str, team_id: str) -> dict[str, Any]:
    projects_payload = _api_get(f"/v1/teams/{team_id}/projects", token)
    projects = projects_payload.get("projects") or []
    matches: list[dict[str, Any]] = []
    all_files: list[dict[str, Any]] = []

    for project in projects:
        pid = project.get("id")
        if not pid:
            continue
        files_payload = _api_get(f"/v1/projects/{pid}/files", token)
        for f in files_payload.get("files") or []:
            row = {
                "project_id": pid,
                "project_name": project.get("name"),
                "file_key": f.get("key"),
                "file_name": f.get("name"),
                "last_modified": f.get("last_modified"),
            }
            all_files.append(row)
            n = _norm_name(str(f.get("name") or ""))
            for target in TARGET_NAMES:
                if _norm_name(target) == n or _norm_name(target) in n or n in _norm_name(target):
                    matches.append(row)

    env_key = _env_value("MKM_CLINIC_LOI_FIGMA_FILE_KEY")
    selected = matches[0] if matches else None
    if not selected and env_key and re.fullmatch(r"[A-Za-z0-9]{8,128}", env_key):
        for row in all_files:
            if row.get("file_key") == env_key:
                selected = row
                break
        if not selected:
            try:
                meta = _api_get(f"/v1/files/{env_key}?depth=1", token)
                selected = {
                    "project_id": None,
                    "project_name": "env_key_direct",
                    "file_key": env_key,
                    "file_name": meta.get("name"),
                    "last_modified": meta.get("lastModified"),
                }
            except urllib.error.HTTPError:
                pass

    return {
        "schema": "clinic_loi_figma_discover_v1",
        "generated_at_utc": _utc(),
        "team_id": team_id,
        "target_names": list(TARGET_NAMES),
        "matches": matches,
        "all_files": all_files,
        "selected": selected,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-ssot", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    token = _figma_token()
    if not token:
        print("FAIL: figma token missing", file=sys.stderr)
        return 1

    try:
        probe = urllib.request.Request(
            "https://api.figma.com/v1/me",
            headers={"X-Figma-Token": token},
        )
        urllib.request.urlopen(probe, timeout=20)
    except urllib.error.HTTPError as exc:
        print(f"FAIL: figma token probe HTTP {exc.code}", file=sys.stderr)
        return 1

    report = discover(token, _team_id())
    selected = report.get("selected")
    report["token_probe_ok"] = True
    report["ok"] = selected is not None

    if selected and args.write_ssot and SSOT.is_file():
        ssot = json.loads(SSOT.read_text(encoding="utf-8-sig"))
        fk = selected["file_key"]
        ssot["figma_file_key"] = fk
        ssot["figma_file_url"] = f"https://www.figma.com/design/{fk}/{selected.get('file_name','mkm-20260624')}"
        ssot["figma_team_id"] = report["team_id"]
        ssot["figma_file_name"] = selected.get("file_name")
        ssot["layer_b_status"] = "active_mkm_20260624"
        ssot["updated_at_utc"] = _utc()
        if "figma_file_name_provisional" in ssot:
            del ssot["figma_file_name_provisional"]
        SSOT.write_text(json.dumps(ssot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "selected": (selected or {}).get("file_key"), "out": str(args.out)}))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
