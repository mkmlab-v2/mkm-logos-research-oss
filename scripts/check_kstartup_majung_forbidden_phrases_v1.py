#!/usr/bin/env python3
"""Scan majung submission graft/paste files for forbidden phrases (denial-aware)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/final/artifacts/k_startup_majung_submission_checklist_v1_latest.json"
GRAFT = ROOT / "docs/final/artifacts/k_startup_majung_submission_graft_v2.md"
PASTE_DIR = ROOT / "reports/kstartup_majung_paste_ready"
OUT = ROOT / "reports/kstartup_majung_forbidden_scan_latest.json"

SKIP_FILES = {
    "bmo0902_disclaimer_paste.txt",
    "00_paste_order.txt",
}

# Affirmative-only patterns (must NOT appear outside denial/exclusion context)
AFFIRMATIVE_PATTERNS = [
    (r"무조건\s*당선", "무조건 당선"),
    (r"TIPS\s*프리패스", "TIPS 프리패스"),
    (r"환각\s*100\s*%\s*제거", "환각 100% 제거"),
    (r"Prophecy\s*Sandbox(?!\s*등)", "Prophecy Sandbox 대외 사용"),
    (r"프로덕션\s*SLA\s*(?:달성|보장|제공|확보)", "프로덕션 SLA 보장"),
    (r"RQ-017|ms-token\s*인과", "RQ-017 ms 인과"),
    (r"수익\s*보장|투자\s*수익\s*보장", "수익 보장"),
    (r"적중률\s*\d|승률\s*\d", "적중률·승률 수치"),
    (r"MS\s*공식\s*협업\s*스타트업\s*(?:으로|입니다|선정)", "MS 공식 협업 단정"),
]

DENIAL_MARKERS = (
    "제외",
    "단정 없",
    "단정하지",
    "약속하지",
    "보장하지",
    "사용하지",
    "언급 금지",
    "금지",
    "아님",
    "하지 않",
    "없음",
    "면책",
    "DRAFT",
    "PoC",
    "후보",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _in_denial_context(text: str, start: int, end: int, window: int = 80) -> bool:
    snippet = text[max(0, start - window) : min(len(text), end + window)]
    return any(m in snippet for m in DENIAL_MARKERS)


def _scan_47_percent(text: str, fname: str) -> list[dict]:
    hits: list[dict] = []
    for m in re.finditer(r"47\s*%", text):
        window = text[max(0, m.start() - 120) : m.end() + 120]
        if "40" not in window and "0.47" not in window:
            hits.append(
                {
                    "file": fname,
                    "match": m.group(0),
                    "label": "47% without 40-case / 0.47 qualifier nearby",
                    "snippet": window.replace("\n", " ").strip()[:160],
                }
            )
    return hits


def _scan_file(path: Path) -> list[dict]:
    if path.name in SKIP_FILES:
        return []
    if not path.is_file():
        return [{"file": path.name, "error": "missing"}]
    text = path.read_text(encoding="utf-8")
    hits: list[dict] = []
    for pattern, label in AFFIRMATIVE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            if _in_denial_context(text, m.start(), m.end()):
                continue
            hits.append(
                {
                    "file": path.name,
                    "match": m.group(0),
                    "label": label,
                    "snippet": text[max(0, m.start() - 30) : m.end() + 30]
                    .replace("\n", " ")
                    .strip(),
                }
            )
    hits.extend(_scan_47_percent(text, path.name))
    return hits


def main() -> int:
    targets: list[Path] = []
    meta_path = ROOT / "reports/kstartup_majung_paste_ready_latest.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for item in meta.get("files") or []:
            rel = item.get("path")
            if rel:
                targets.append(ROOT / rel)
    if GRAFT.is_file() and GRAFT not in targets:
        targets.insert(0, GRAFT)
    if not targets:
        if GRAFT.is_file():
            targets.append(GRAFT)
        if PASTE_DIR.is_dir():
            targets.extend(sorted(PASTE_DIR.glob("bmo0902_*.txt")))

    all_hits: list[dict] = []
    for p in targets:
        all_hits.extend(_scan_file(p))

    ok = len(all_hits) == 0
    report = {
        "schema": "kstartup_majung_forbidden_scan_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "targets_scanned": len(targets),
        "hit_count": len(all_hits),
        "hits": all_hits,
        "boundary_ack": "Scan pass does not imply eligibility or selection.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "hit_count": len(all_hits), "out": OUT.as_posix()}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
