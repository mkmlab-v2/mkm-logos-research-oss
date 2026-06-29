#!/usr/bin/env python3
"""OI 20460237 paste pack gate — forbidden grep, cross-program isolation, lock lengths."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATTERNS = [
    re.compile(r"47\s*\.?\s*5\s*%", re.I),
    re.compile(r"Track\s*A", re.I),
    re.compile(r"실매매"),
    re.compile(r"자동\s*제출"),
    re.compile(r"당선\s*확정"),
    re.compile(r"탈락\s*확정"),
    re.compile(r"금융\s*심사\s*대체"),
    re.compile(r"100\s*%"),
    re.compile(r"무결점"),
    re.compile(r"무조건"),
]

# 327/340 paste가 OI에 섞이면 FAIL (negation 라인 제외)
CROSS_PROGRAM_FORBIDDEN = [
    re.compile(r"정책자금\s*융자"),
    re.compile(r"OpenData"),
    re.compile(r"기보\)?\s*자동판별"),
    re.compile(r"창업도약패키지"),
    re.compile(r"340호"),
]

CROSS_PROGRAM_FIELDS = (
    "step4_tsksNm.txt",
    "step4_tsksCtnt.txt",
    "step2_majrProd.txt",
)

REQUIRED_MARKERS = {
    "step4_tsksNm.txt": (re.compile(r"RPA|RPA를"), "OI 과제명에 RPA 협업과제 표기 필요"),
    "step4_tsksCtnt.txt": (re.compile(r"한국평가데이터"), "OI 과제내용에 수요기업 한국평가데이터 필요"),
    "step2_majrProd.txt": (re.compile(r"RPA|OCR"), "OI 주생산품에 RPA/OCR 표기 필요"),
}

NEGATION_MARKERS = (
    "주장하지",
    "대체하지",
    "없음",
    "금지",
    "합선",
    "배제",
    "단정",
    "미연결",
    "HOLD",
    "복사 금지",
)

EXPECTED_FIELD_COUNT = 11
LOCK_VERSION = "v2.0-lock"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _line_excluded(line: str) -> bool:
    return any(m in line for m in NEGATION_MARKERS)


def _forbidden_hits(text: str, *, source: str, patterns: list[re.Pattern[str]]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if _line_excluded(line):
            continue
        for pat in patterns:
            if pat.search(line):
                hits.append(
                    {
                        "source": source,
                        "line": i,
                        "pattern": pat.pattern,
                        "excerpt": line[:160],
                    }
                )
    return hits


def verify_paste_pack(root: Path = ROOT) -> tuple[bool, list[str], dict[str, object]]:
    errors: list[str] = []
    hits: list[dict[str, object]] = []
    cross_hits: list[dict[str, object]] = []
    meta: dict[str, object] = {}

    sys.path.insert(0, str(root / "scripts"))
    try:
        from build_kstartup_open_innovation_20460237_paste_ready_v1 import (  # noqa: WPS433
            FIELDS,
            HTML_OUT,
            LOCK_VERSION as BUILD_LOCK_VERSION,
            PASTE_DIR,
        )
    except ImportError as exc:
        return False, [f"import_build_script: {exc}"], meta

    meta["field_count"] = len(FIELDS)
    meta["lock_version"] = BUILD_LOCK_VERSION
    if len(FIELDS) != EXPECTED_FIELD_COUNT:
        errors.append(f"field_count expected {EXPECTED_FIELD_COUNT} got {len(FIELDS)}")

    lock_lengths = {
        "oi_tech_differentiation_v1_lock.txt": len(FIELDS["oi_tech_differentiation_v1_lock.txt"]),
        "oi_risk_defense_v1_lock.txt": len(FIELDS["oi_risk_defense_v1_lock.txt"]),
    }
    meta["lock_lengths"] = lock_lengths

    lengths: dict[str, int] = {}
    for fname, text in FIELDS.items():
        lengths[fname] = len(text)
        hits.extend(_forbidden_hits(text, source=fname, patterns=FORBIDDEN_PATTERNS))
        if fname in CROSS_PROGRAM_FIELDS:
            cross_hits.extend(
                _forbidden_hits(text, source=fname, patterns=CROSS_PROGRAM_FORBIDDEN)
            )
            pat, msg = REQUIRED_MARKERS[fname]
            if not pat.search(text):
                errors.append(f"required_marker_missing: {fname} — {msg}")
    meta["lengths"] = lengths
    meta["cross_program_hits"] = cross_hits
    if cross_hits:
        errors.append(f"cross_program_forbidden: {len(cross_hits)}")

    PASTE_DIR.mkdir(parents=True, exist_ok=True)
    for fname, text in FIELDS.items():
        path = PASTE_DIR / fname
        if not path.is_file():
            errors.append(f"missing_paste_file: {fname}")
            continue
        disk = path.read_text(encoding="utf-8")
        if disk != text:
            errors.append(f"paste_file_stale: {fname} (re-run build script)")

    if not HTML_OUT.is_file():
        errors.append(f"missing_html: {HTML_OUT}")
    else:
        html = HTML_OUT.read_text(encoding="utf-8")
        for fname in FIELDS:
            eid = "t_" + fname.replace(".", "_")
            if eid not in html:
                errors.append(f"html_missing_section_id: {eid}")
        hits.extend(_forbidden_hits(html, source="paste_assistant.html", patterns=FORBIDDEN_PATTERNS))

    meta["forbidden_hits"] = hits
    if hits:
        errors.append(f"forbidden_grep_hits: {len(hits)}")

    return len(errors) == 0, errors, meta


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "reports/kstartup_open_innovation_20460237_paste_gate_latest.json",
    )
    args = ap.parse_args()

    ok, errors, meta = verify_paste_pack()
    doc = {
        "schema": "kstartup_open_innovation_20460237_paste_gate_v1",
        "generated_at_utc": _utc(),
        "pms_task_id": "20460237",
        "deadline_kst": "2026-06-15T16:00:00+09:00",
        "ok": ok,
        "errors": errors,
        "lock_version": LOCK_VERSION,
        **meta,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not ok:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "out": str(args.out), **meta}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
