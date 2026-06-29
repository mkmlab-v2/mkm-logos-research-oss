"""One-off NGC .env smoke — prints status only, never secrets."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _parse_env_tail() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return out
    for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("nvapi-"):
            out["_MALFORMED_BARE_NVAPI"] = "yes"
        if "=" in s:
            k, _, v = s.partition("=")
            out[k.strip()] = v.strip()
    return out


def _load_dotenv() -> tuple[str | None, str | None]:
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass
    return os.getenv("NGC_API_KEY"), os.getenv("NGC_ORG")


def _nim_models_smoke(api_key: str) -> dict:
    url = "https://integrate.api.nvidia.com/v1/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data") if isinstance(data, dict) else None
            count = len(models) if isinstance(models, list) else None
            return {
                "ok": resp.status == 200,
                "http_status": resp.status,
                "model_count": count,
                "error": None,
            }
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {
            "ok": False,
            "http_status": e.code,
            "model_count": None,
            "error": err_body or str(e),
        }
    except Exception as e:
        return {"ok": False, "http_status": None, "model_count": None, "error": str(e)}


def _tao_login_smoke(api_key: str, org: str) -> dict:
    url = "https://api.tao.ngc.nvidia.com/api/v2/login"
    body = json.dumps({"ngc_key": api_key, "ngc_org_name": org}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("token") or data.get("access_token")
            return {
                "ok": bool(token),
                "http_status": resp.status,
                "has_token": bool(token),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return {
            "ok": False,
            "http_status": e.code,
            "has_token": False,
            "error": err_body or str(e),
        }
    except Exception as e:
        return {"ok": False, "http_status": None, "has_token": False, "error": str(e)}


def main() -> int:
    raw = _parse_env_tail()
    key, org = _load_dotenv()
    if not key and "NGC_API_KEY" in raw:
        key = raw["NGC_API_KEY"]
    if not org and "NGC_ORG" in raw:
        org = raw["NGC_ORG"]

    nvidia_alias = os.getenv("NVIDIA_API_KEY")
    report: dict = {
        "env_file": str(ENV_PATH),
        "malformed_bare_nvapi_line": raw.get("_MALFORMED_BARE_NVAPI") == "yes",
        "NGC_API_KEY_set": bool(key),
        "NGC_API_KEY_len": len(key) if key else 0,
        "NGC_API_KEY_prefix_ok": bool(key and key.startswith("nvapi-")),
        "NVIDIA_API_KEY_set": bool(nvidia_alias),
        "NVIDIA_API_KEY_matches_ngc": bool(
            key and nvidia_alias and key == nvidia_alias
        ),
        "NGC_ORG_set": bool(org),
        "NGC_ORG_numeric": bool(org and re.fullmatch(r"\d+", org)),
        "python_dotenv_loaded": bool(os.getenv("NGC_API_KEY")),
    }

    if key:
        report["nim_models_smoke"] = _nim_models_smoke(key)
    else:
        report["nim_models_smoke"] = {"skipped": True, "reason": "missing NGC_API_KEY"}

    if key and org:
        report["tao_login_smoke"] = _tao_login_smoke(key, org)
    else:
        report["tao_login_smoke"] = {"skipped": True, "reason": "missing key or org"}

    out_path = ROOT / "reports" / "ngc_env_check_v1_latest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report.get("malformed_bare_nvapi_line"):
        return 2
    nim = report.get("nim_models_smoke") or {}
    if nim.get("skipped"):
        return 1
    if nim.get("ok"):
        return 0
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
