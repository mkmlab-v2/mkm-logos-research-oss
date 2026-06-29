#!/usr/bin/env python3
"""Audit GitHub · X · Reddit public UR presence vs Fact-Lock SSOT [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/universal_root_public_channels_audit_v1_latest.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
PHASE1A = ROOT / "reports/universal_root_phase1a_baseline_compare_v1_latest.json"
PUBLIC_README = ROOT / "exports/mkm-universal-root-v1/README.md"
PUSH_MIRROR = ROOT / "exports/_push-mkm-universal-root"
FORBIDDEN = [
    "gpt killer",
    "gpt-killer",
    "global hallucination rate",
    "99.53% compression",
    "47.5%",
    "neuro-symbolic revolution",
    "partial_complete",
]

PASTE_FILES = {
    "reddit_title": ROOT / "reports/human_paste/universal_root_reddit_title.txt",
    "reddit_body": ROOT / "reports/human_paste/universal_root_reddit_body.md",
    "x_post_1": ROOT / "reports/human_paste/universal_root_x_post_1.txt",
    "x_post_2": ROOT / "reports/human_paste/universal_root_x_post_2.txt",
    "x_post_3": ROOT / "reports/human_paste/universal_root_x_post_3.txt",
    "x_post_4": ROOT / "reports/human_paste/universal_root_x_post_4.txt",
}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return proc.returncode, (proc.stdout or proc.stderr or "").strip()


def _gh_json(args: list[str]) -> Any:
    code, out = _run(["gh", "api", *args])
    if code != 0:
        return {"error": out[:500]}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out[:500]}


def _scan_forbidden(text: str) -> list[str]:
    low = text.lower()
    hits: list[str] = []
    for phrase in FORBIDDEN:
        if phrase not in low:
            continue
        if phrase == "global hallucination rate":
            if 'not "global hallucination rate"' in low or "not a global hallucination rate" in low:
                continue
            if "not claiming" in low and "global hallucination" in low:
                continue
        if phrase == "47.5%":
            if "not in this export" in low or "compression kpi lane" in low:
                continue
        hits.append(phrase)
    return hits


def _pct_from_phase1a(method_id: str) -> str | None:
    if not PHASE1A.is_file():
        return None
    doc = json.loads(PHASE1A.read_text(encoding="utf-8-sig"))
    for m in doc.get("methods") or []:
        if m.get("id") == method_id and m.get("primary_value") is not None:
            return f"{float(m['primary_value']) * 100:.2f}%"
    return None


def audit_github() -> dict[str, Any]:
    repo = _gh_json(["repos/mkmlab-v2/mkm-universal-root", "--jq", "."])
    readme_api = _gh_json(["repos/mkmlab-v2/mkm-universal-root/readme"])
    live_readme = ""
    if isinstance(readme_api, dict) and readme_api.get("content"):
        live_readme = base64.b64decode(readme_api["content"]).decode("utf-8", errors="replace")

    local_readme = PUBLIC_README.read_text(encoding="utf-8-sig") if PUBLIC_README.is_file() else ""
    mirror_readme = ""
    mirror_path = PUSH_MIRROR / "README.md"
    if mirror_path.is_file():
        mirror_readme = mirror_path.read_text(encoding="utf-8-sig")

    comments = _gh_json(["repos/mkmlab-v2/mkm-universal-root/discussions/2/comments"])
    author_comments = []
    if isinstance(comments, list):
        author_comments = [c for c in comments if (c.get("user") or {}).get("login") == "mkmlab-v2"]

    b0 = _pct_from_phase1a("B0")
    b3 = _pct_from_phase1a("B3")
    readme_checks = {
        "live_has_phase1a_section": "Phase 1A" in live_readme,
        "live_has_b0_pct": bool(b0 and b0 in live_readme),
        "live_has_b3_pct": bool(b3 and b3 in live_readme),
        "mirror_has_phase1a_section": "Phase 1A" in mirror_readme,
        "local_has_phase1a_section": "Phase 1A" in local_readme,
    }
    issues: list[str] = []
    if not readme_checks["live_has_phase1a_section"]:
        issues.append("github_readme_missing_phase1a_live")
    if b0 and not readme_checks["live_has_b0_pct"]:
        issues.append("github_readme_missing_b0_live")
    if len(author_comments) > 5:
        issues.append("github_discussions_author_comment_spam")

    mirror_dirty = False
    if PUSH_MIRROR.is_dir():
        code, status = _run(["git", "-C", str(PUSH_MIRROR), "status", "--porcelain"])
        mirror_dirty = code == 0 and bool(status.strip())

    return {
        "platform": "github",
        "repo": "mkmlab-v2/mkm-universal-root",
        "stars": repo.get("stargazers_count") if isinstance(repo, dict) else None,
        "forks": repo.get("forks_count") if isinstance(repo, dict) else None,
        "pushed_at": repo.get("pushed_at") if isinstance(repo, dict) else None,
        "description": repo.get("description") if isinstance(repo, dict) else None,
        "discussion_url": "https://github.com/mkmlab-v2/mkm-universal-root/discussions/2",
        "author_comment_count": len(author_comments),
        "author_comment_ids": [c.get("id") for c in author_comments],
        "readme_checks": readme_checks,
        "mirror_unpushed": mirror_dirty,
        "forbidden_in_live_readme": _scan_forbidden(live_readme),
        "issues": issues,
    }


def audit_paste_ssot() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    issues: list[str] = []
    for key, path in PASTE_FILES.items():
        text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
        bad = _scan_forbidden(text)
        rows[key] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "chars": len(text),
            "forbidden_hits": bad,
            "has_phase1a_b0": "78.04%" in text or "english_only" in text.lower(),
            "has_fixture_scope": "fixture" in text.lower() or "500-pair" in text.lower(),
        }
        if bad:
            issues.append(f"paste_forbidden_{key}")
        if key.startswith("reddit") and "$0 infra" in text.lower():
            issues.append("reddit_title_dollar_zero_infra_hype")
    return {"paste_ssot": rows, "issues": issues}


def audit_x(gtm: dict[str, Any]) -> dict[str, Any]:
    x = (gtm.get("channels") or {}).get("x") or {}
    urls = x.get("post_urls") or {}
    issues: list[str] = []
    if x.get("status") == "posted_1_4" and len(urls) < 4:
        issues.append("x_missing_post_urls_in_gtm")
    return {
        "platform": "x",
        "handle": "moksorinw",
        "status": x.get("status"),
        "known_post_urls": urls,
        "issues": issues,
        "live_edit_note": "X posts are not editable; use correction reply paste if copy drifted",
        "correction_paste": "reports/human_paste/universal_root_x_public_correction_v1.txt",
    }


def audit_reddit(gtm: dict[str, Any]) -> dict[str, Any]:
    rd = (gtm.get("channels") or {}).get("reddit_local_llm") or {}
    issues: list[str] = []
    if not rd.get("post_url"):
        issues.append("reddit_post_url_missing_in_gtm")
    return {
        "platform": "reddit",
        "subreddit": rd.get("subreddit", "LocalLLM"),
        "status": rd.get("status"),
        "post_url": rd.get("post_url"),
        "issues": issues,
        "live_edit_note": "Reddit posts are not editable; use correction comment paste",
        "correction_paste": "reports/human_paste/universal_root_reddit_public_correction_v1.md",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    gtm = json.loads(GTM.read_text(encoding="utf-8-sig")) if GTM.is_file() else {}
    gh = audit_github()
    paste = audit_paste_ssot()
    x = audit_x(gtm)
    reddit = audit_reddit(gtm)

    all_issues = gh.get("issues", []) + paste.get("issues", [])
    open_gaps = x.get("issues", []) + reddit.get("issues", [])

    doc = {
        "schema": "universal_root_public_channels_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "channels": [gh, paste, x, reddit],
        "gtm_freeze_active": (gtm.get("gtm_freeze") or {}).get("active"),
        "external_repro_count": (gtm.get("channels") or {}).get("github_discussions", {}).get("external_repro_reports", 0),
        "issues": all_issues,
        "open_gaps": open_gaps,
        "ok": not all_issues,
        "reproduce": "py scripts/audit_universal_root_public_channels_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "issue_count": len(all_issues), "open_gaps": len(open_gaps), "out": str(args.out)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
