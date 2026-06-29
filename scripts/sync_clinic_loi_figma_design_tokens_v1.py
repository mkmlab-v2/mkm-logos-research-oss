#!/usr/bin/env python3
"""Sync + validate clinic LOI Figma token map against DTCG SSOT.

Writes reports/clinic_loi_figma_design_sync_v1_latest.json
Optional --fetch-figma when MKM_CLINIC_LOI_FIGMA_FILE_KEY + Figma token set.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "docs/final/artifacts/clinic_loi_figma_token_map_v1.json"
DESIGN_SSOT = ROOT / "docs/final/artifacts/clinic_loi_figma_design_ssot_v1_latest.json"
DTCG = ROOT / "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json"
PREVIEW = ROOT / "reports/clinic_km_mmp_loi_preview_v1.html"
DEFAULT_OUT = ROOT / "reports/clinic_loi_figma_design_sync_v1_latest.json"
TOKENS_STUDIO_OUT = ROOT / "reports/clinic_loi_figma_tokens_studio_export_v1.json"
DISCOVER_PATH = ROOT / "reports/clinic_loi_figma_discover_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_value(name: str) -> str | None:
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
    for key in ("FIGMA_ACCESS_TOKEN", "MKM_FIGMA_ACCESS_TOKEN"):
        val = _env_value(key)
        if val:
            return val
    return None


def _figma_file_key(map_doc: dict, ssot: dict) -> str | None:
    env_name = str(map_doc.get("figma_file_key_env") or ssot.get("figma_file_key_env") or "")
    if env_name:
        val = _env_value(env_name)
        if val:
            return val
    for doc in (map_doc, ssot):
        key = doc.get("figma_file_key")
        if key:
            return str(key).strip()
    return None


def _hex_norm(value: str) -> str:
    return value.strip().lower()


def validate_map_against_dtcg(map_doc: dict, dtcg_doc: dict) -> list[str]:
    errors: list[str] = []
    resolved = dtcg_doc.get("css_variables_resolved") or {}
    for row in map_doc.get("variables") or []:
        css_var = row.get("css_var")
        expected = str(row.get("value", ""))
        if not css_var:
            errors.append(f"missing_css_var:{row.get('figma_name')}")
            continue
        actual = str(resolved.get(css_var, ""))
        if not actual:
            errors.append(f"dtcg_missing:{css_var}")
            continue
        if expected.startswith("#"):
            if _hex_norm(actual) != _hex_norm(expected):
                errors.append(f"dtcg_mismatch:{css_var}:{expected}!={actual}")
        elif actual != expected:
            errors.append(f"dtcg_mismatch:{css_var}:{expected}!={actual}")
    preview = PREVIEW.read_text(encoding="utf-8") if PREVIEW.is_file() else ""
    if "--clinic-loi-bg" not in preview or "근거 없으면" not in preview:
        errors.append("preview_missing_clinic_loi_markers")
    return errors


def _normalize_figma_file_key(raw: str) -> str:
    raw = raw.strip().strip('"').strip("'")
    url_match = re.search(r"figma\.com/(?:design|file|proto)/([A-Za-z0-9]+)", raw)
    if url_match:
        return url_match.group(1)
    return raw


def _figma_file_key_format_ok(key: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{8,128}", key))


def probe_figma_token(token: str) -> tuple[bool, int | None, str | None]:
    req = urllib.request.Request(
        "https://api.figma.com/v1/me",
        headers={"X-Figma-Token": token},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200, resp.status, None
    except urllib.error.HTTPError as exc:
        return False, exc.code, f"figma_token_http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, None, f"figma_token_error:{type(exc).__name__}"


def probe_figma_file(file_key: str, token: str, retries: int = 4) -> tuple[bool, int | None, str | None]:
    url = f"https://api.figma.com/v1/files/{file_key}?depth=1"
    last_code: int | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"X-Figma-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.status == 200, resp.status, None
        except urllib.error.HTTPError as exc:
            last_code = exc.code
            if exc.code == 429 and attempt < retries:
                import time

                time.sleep(5.0 * (attempt + 1))
                continue
            return False, exc.code, f"figma_file_http_{exc.code}"
        except Exception as exc:  # noqa: BLE001
            return False, None, f"figma_file_error:{type(exc).__name__}"
    return False, last_code, f"figma_file_http_{last_code}"


def _parse_utc(ts: str) -> datetime | None:
    try:
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def discover_recent_ok(file_key: str, max_age_minutes: int = 60) -> dict[str, Any] | None:
    if not DISCOVER_PATH.is_file():
        return None
    try:
        doc = json.loads(DISCOVER_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    if not doc.get("ok") or not doc.get("token_probe_ok"):
        return None
    selected = doc.get("selected") or {}
    if selected.get("file_key") != file_key:
        return None
    generated = _parse_utc(str(doc.get("generated_at_utc", "")))
    if not generated:
        return None
    age = datetime.now(timezone.utc) - generated
    if age.total_seconds() > max_age_minutes * 60:
        return None
    return {
        "file_name": selected.get("file_name"),
        "generated_at_utc": doc.get("generated_at_utc"),
        "age_seconds": int(age.total_seconds()),
    }


def fetch_figma_variable_map(file_key: str, token: str) -> tuple[dict[str, str] | None, str | None]:
    url = f"https://api.figma.com/v1/files/{file_key}/variables/local"
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, f"figma_api_http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return None, f"figma_api_error:{type(exc).__name__}"

    meta = payload.get("meta") or {}
    variables = meta.get("variables") or {}
    out: dict[str, str] = {}
    for var in variables.values():
        name = var.get("name")
        if not name:
            continue
        values = var.get("valuesByMode") or {}
        if not values:
            continue
        raw = next(iter(values.values()))
        if isinstance(raw, dict) and {"r", "g", "b"} <= set(raw.keys()):
            r = int(round(float(raw["r"]) * 255))
            g = int(round(float(raw["g"]) * 255))
            b = int(round(float(raw["b"]) * 255))
            out[name] = f"#{r:02x}{g:02x}{b:02x}"
        else:
            out[name] = str(raw)
    return out, None


def validate_figma_live(map_doc: dict, live: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for row in map_doc.get("variables") or []:
        name = row.get("figma_name")
        if not name or name not in live:
            errors.append(f"figma_live_missing:{name}")
            continue
        expected = str(row.get("value", ""))
        actual = live[name]
        if expected.startswith("#"):
            if _hex_norm(actual) != _hex_norm(expected):
                errors.append(f"figma_live_drift:{name}")
        elif actual != expected and actual != expected.replace("px", ""):
            errors.append(f"figma_live_drift:{name}")
    return errors


def export_tokens_studio(dtcg_doc: dict) -> dict[str, Any]:
    return {
        "schema": "clinic_loi_figma_tokens_studio_export_v1",
        "generated_at_utc": _utc(),
        "import_hint": "Tokens Studio: import this JSON or reports/clinic_km_mmp_landing_tokens_v2.dtcg.json",
        "preset": dtcg_doc.get("preset"),
        "dtcg": dtcg_doc,
        "css_variables_resolved": dtcg_doc.get("css_variables_resolved"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fetch-figma", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    map_doc = json.loads(MAP_PATH.read_text(encoding="utf-8-sig"))
    ssot = json.loads(DESIGN_SSOT.read_text(encoding="utf-8-sig"))
    dtcg_doc = json.loads(DTCG.read_text(encoding="utf-8-sig"))

    if map_doc.get("schema") != "clinic_loi_figma_token_map_v1":
        errors.append("token_map_schema_mismatch")

    errors.extend(validate_map_against_dtcg(map_doc, dtcg_doc))

    studio_doc = export_tokens_studio(dtcg_doc)
    TOKENS_STUDIO_OUT.write_text(json.dumps(studio_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    figma_api_status = "skipped"
    figma_live: dict[str, str] | None = None
    file_key_raw = _figma_file_key(map_doc, ssot)
    file_key = _normalize_figma_file_key(file_key_raw) if file_key_raw else None
    figma_diagnostics: dict[str, Any] = {}

    if args.fetch_figma:
        token = _figma_token()
        if not token:
            figma_api_status = "token_missing"
            errors.append("figma_token_missing")
        elif not file_key:
            figma_api_status = "file_key_missing"
            errors.append("figma_file_key_missing")
        else:
            figma_diagnostics["file_key_format_ok"] = _figma_file_key_format_ok(file_key)
            if not figma_diagnostics["file_key_format_ok"]:
                errors.append("figma_file_key_format_invalid")
                figma_api_status = "file_key_format_invalid"
            token_ok, token_http, token_err = probe_figma_token(token)
            figma_diagnostics["token_probe_ok"] = token_ok
            figma_diagnostics["token_probe_http"] = token_http
            if not token_ok:
                errors.append(token_err or "figma_token_probe_failed")
                figma_api_status = token_err or "figma_token_probe_failed"
            elif figma_diagnostics.get("file_key_format_ok"):
                file_ok, file_http, file_err = probe_figma_file(file_key, token)
                figma_diagnostics["file_probe_ok"] = file_ok
                figma_diagnostics["file_probe_http"] = file_http
                if not file_ok and file_http == 429:
                    fb = discover_recent_ok(file_key)
                    if fb:
                        file_ok = True
                        figma_diagnostics["file_probe_ok"] = True
                        figma_diagnostics["file_probe_fallback"] = "discover_recent_ok"
                        figma_diagnostics["discover_fallback"] = fb
                        figma_api_status = "figma_file_rate_limited_discover_ok"
                if not file_ok:
                    errors.append(file_err or "figma_file_probe_failed")
                    figma_api_status = file_err or "figma_file_probe_failed"
                else:
                    figma_live, fetch_status = fetch_figma_variable_map(file_key, token)
                    if figma_live is None:
                        if fetch_status == "figma_api_http_403":
                            figma_diagnostics["variables_tier"] = "starter_file_only"
                            figma_api_status = "variables_api_403_starter_ok"
                        elif fetch_status == "figma_api_http_429":
                            fb = discover_recent_ok(file_key)
                            if fb:
                                figma_diagnostics["variables_tier"] = "starter_file_only"
                                figma_diagnostics["variables_fetch_fallback"] = "rate_limited_assume_starter"
                                figma_api_status = "variables_api_429_discover_ok"
                            else:
                                errors.append(f"figma_fetch_failed:{fetch_status}")
                                figma_api_status = fetch_status
                        else:
                            errors.append(f"figma_fetch_failed:{fetch_status}")
                            figma_api_status = fetch_status
                    else:
                        figma_api_status = fetch_status or "ok"
                        errors.extend(validate_figma_live(map_doc, figma_live))

    ok = len(errors) == 0
    doc = {
        "schema": "clinic_loi_figma_design_sync_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "send_gate": "HOLD",
        "lane_status": "frozen_deferred",
        "local_map_ok": len(validate_map_against_dtcg(map_doc, dtcg_doc)) == 0,
        "figma_api_status": figma_api_status,
        "figma_file_key_present": bool(file_key),
        "figma_diagnostics": figma_diagnostics,
        "figma_setup_hint_ko": (
            "Figma Settings → Security → Personal access tokens (file_content:read 권장). "
            "MKM_CLINIC_LOI_FIGMA_FILE_KEY = figma.com/design/{KEY}/... URL의 KEY(영숫자)만."
        ),
        "errors": errors,
        "artifacts": {
            "token_map": str(MAP_PATH.relative_to(ROOT)).replace("\\", "/"),
            "tokens_studio_export": str(TOKENS_STUDIO_OUT.relative_to(ROOT)).replace("\\", "/"),
            "dtcg": str(DTCG.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "figma_api_status": figma_api_status, "errors": len(errors)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
