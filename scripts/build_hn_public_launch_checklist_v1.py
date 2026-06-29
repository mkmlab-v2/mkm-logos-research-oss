#!/usr/bin/env python3
"""HN public launch checklist M-bundle — secret scan, solo OSS, paste/README alignment.

  py scripts/build_hn_public_launch_checklist_v1.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASTE_JSON = ROOT / "reports/hangul_ko_lemma_hn_launch_paste_v1_latest.json"
PASTE_MD = ROOT / "reports/hangul_ko_lemma_hn_launch_paste_v1_latest.md"
README = ROOT / "README.md"
PUBLIC_FACING = ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
SECRET_OUT = ROOT / "reports/mkm_secret_pattern_scan_v1_latest.json"
OSS_OUT = ROOT / "reports/mkm_solo_oss_release_readiness_v1_latest.json"
OUT = ROOT / "reports/hn_public_launch_checklist_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _run_py(script: str, *extra: str) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *extra]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or "") + (proc.stderr or "")
    return int(proc.returncode), tail.strip()[-500:]


def _extract_main_post(md: str) -> str:
    m = re.search(
        r"(?ms)^## Post body — MAIN \(paste into Show HN submission\)\s*\n(.*?)(?=^## |\Z)",
        md,
    )
    return m.group(1).strip() if m else ""


def _readme_show_hn_block(text: str) -> str:
    m = re.search(r"(?ms)^## Show HN / community blurb.*?(?=^## |\Z)", text)
    return m.group(0) if m else ""


def _paste_public_facing_checks(main_post: str, one_liner: str) -> dict[str, Any]:
    text = f"{main_post}\n{one_liner}".lower()
    deny_live = "live trading" in text and ("do not claim" in text or "not claim" in text)
    deny_moat = ("sla moat" in text or "moat" in text) and "do not claim" in text
    secret_patterns = [
        r"sk-[a-z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----",
        r"api[_-]?key\s*[:=]\s*['\"]?[a-z0-9]{16,}",
    ]
    secret_hits = [p for p in secret_patterns if re.search(p, text, re.I)]
    return {
        "PF_no_secrets_in_public_copy": {
            "ok": not secret_hits,
            "secret_pattern_hits": secret_hits,
        },
        "PF_no_live_trading_implication": {
            "ok": deny_live or "live trading" not in text,
            "note": "MAIN disclaims live trading" if deny_live else None,
        },
        "PF_ip_moat_not_claimed": {
            "ok": deny_moat or ("sla" not in text and "moat" not in text),
            "note": "MAIN disclaims SLA moat" if deny_moat else None,
        },
        "all_pass": not secret_hits
        and (deny_live or "live trading" not in text)
        and (deny_moat or ("sla" not in text and "moat" not in text)),
    }


def _alignment_checks(paste: dict[str, Any], readme_text: str, main_post: str) -> dict[str, Any]:
    hn_block = _readme_show_hn_block(readme_text)
    needles = [
        ("paste_ssot_pointer", "hangul_ko_lemma_hn_launch_paste_v1_latest.md"),
        ("metric_9962_live", "99.62"),
        ("metric_4712_golden40", "47.12"),
        ("gatekeeper_bypass", "gatekeeper"),
        ("three_benches_never_blend", "never merge"),
        ("no_git_clone_premise", "not `git clone` today"),
    ]
    rows: dict[str, bool] = {}
    for key, needle in needles:
        in_readme = needle.lower() in hn_block.lower()
        in_paste = needle.lower() in main_post.lower() or needle.lower() in (paste.get("one_liner") or "").lower()
        if key == "paste_ssot_pointer":
            rows[key] = in_readme
        else:
            rows[key] = in_readme and in_paste
    return {
        "readme_show_hn_block_chars": len(hn_block),
        "checks": rows,
        "all_pass": all(rows.values()),
    }


def main() -> int:
    steps: dict[str, Any] = {}

    rc_secret, tail_secret = _run_py("check_mkm_secret_patterns_v1.py")
    secret_doc = json.loads(SECRET_OUT.read_text(encoding="utf-8")) if SECRET_OUT.is_file() else {}
    steps["secret_pattern_scan"] = {
        "script": "check_mkm_secret_patterns_v1.py",
        "exit_code": rc_secret,
        "ok": rc_secret == 0 and secret_doc.get("ok"),
        "artifact": _rel(SECRET_OUT),
        "finding_count": secret_doc.get("finding_count"),
        "tail": tail_secret,
    }

    rc_oss, tail_oss = _run_py("check_mkm_solo_oss_release_readiness_v1.py")
    oss_doc = json.loads(OSS_OUT.read_text(encoding="utf-8")) if OSS_OUT.is_file() else {}
    steps["solo_oss_release_readiness"] = {
        "script": "check_mkm_solo_oss_release_readiness_v1.py",
        "exit_code": rc_oss,
        "ok": rc_oss == 0 and oss_doc.get("ok"),
        "artifact": _rel(OSS_OUT),
        "errors": oss_doc.get("errors"),
        "tail": tail_oss,
    }

    paste: dict[str, Any] = {}
    if PASTE_JSON.is_file():
        paste = json.loads(PASTE_JSON.read_text(encoding="utf-8"))
    main_post = _extract_main_post(PASTE_MD.read_text(encoding="utf-8")) if PASTE_MD.is_file() else ""
    readme_text = README.read_text(encoding="utf-8") if README.is_file() else ""
    align = _alignment_checks(paste, readme_text, main_post)

    steps["paste_ssot"] = {
        "artifact_md": _rel(PASTE_MD) if PASTE_MD.is_file() else None,
        "artifact_json": _rel(PASTE_JSON) if PASTE_JSON.is_file() else None,
        "paste_build_ok": paste.get("paste_build_ok"),
        "paste_copy_approved": paste.get("paste_copy_approved"),
        "commander_signoff_at": paste.get("commander_signoff_at"),
        "send_gate": paste.get("send_gate", "HOLD"),
    }

    steps["readme_paste_alignment"] = align

    pf = _paste_public_facing_checks(main_post, paste.get("one_liner") or "")
    steps["paste_public_facing_scan"] = pf

    public_facing_manual = [
        {
            "id": "PF_no_secrets_in_public_copy",
            "status": "pass" if pf["PF_no_secrets_in_public_copy"]["ok"] else "fail",
            "ssot": _rel(PUBLIC_FACING) if PUBLIC_FACING.is_file() else None,
            "auto_scan": pf["PF_no_secrets_in_public_copy"],
        },
        {
            "id": "PF_no_live_trading_implication",
            "status": "pass" if pf["PF_no_live_trading_implication"]["ok"] else "fail",
            "note": pf["PF_no_live_trading_implication"].get("note")
            or "paste MAIN includes no live trading claim",
        },
        {
            "id": "PF_ip_moat_not_claimed",
            "status": "pass" if pf["PF_ip_moat_not_claimed"]["ok"] else "fail",
            "note": pf["PF_ip_moat_not_claimed"].get("note")
            or "paste includes no exclusive moat / SLA %",
        },
        {
            "id": "commander_signoff_paste",
            "status": "pass" if paste.get("commander_signoff_at") else "pending",
            "action": "py scripts/build_hangul_ko_lemma_hn_launch_paste_v1.py --commander-signoff \"OK\"",
        },
        {
            "id": "push_github_explicit",
            "status": "blocked",
            "action": "scripts/Push-GitHub-Explicit.ps1 -Acknowledge",
        },
        {
            "id": "send_gate_unlock",
            "status": "blocked",
            "note": "Show HN send remains HOLD until explicit unlock",
        },
    ]

    signoff_ok = bool(paste.get("commander_signoff_at"))
    automated_ok = (
        steps["secret_pattern_scan"]["ok"]
        and steps["solo_oss_release_readiness"]["ok"]
        and align["all_pass"]
        and pf["all_pass"]
        and paste.get("paste_build_ok")
        and signoff_ok
    )

    next_human: list[str] = []
    if not pf["all_pass"]:
        next_human.append("Fix paste PUBLIC_FACING scan failures and rebuild checklist.")
    if not signoff_ok:
        next_human.append(
            'Commander signoff: build_hangul_ko_lemma_hn_launch_paste_v1.py --commander-signoff "OK"'
        )
    if automated_ok:
        next_human.append(
            "Paste copy ready — Show HN post only after send_gate unlock + Push-GitHub-Explicit (separate orders)."
        )
    else:
        next_human.append("Complete remaining automated checklist failures before public send.")
    next_human.append("If public repo intended: Push-GitHub-Explicit.ps1 -Acknowledge (separate order).")

    doc = {
        "schema": "hn_public_launch_checklist_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "stage": 2,
        "reproduce": "py scripts/build_hn_public_launch_checklist_v1.py",
        "automated_ok": automated_ok,
        "send_gate": "HOLD",
        "github_public": "blocked_until_Push-GitHub-Explicit",
        "steps": steps,
        "public_facing_manual": public_facing_manual,
        "next_human_steps": next_human,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"wrote": _rel(OUT), "automated_ok": automated_ok}, ensure_ascii=False))
    return 0 if automated_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
