#!/usr/bin/env python3
"""Smoke logos inquiry beta Q&A — representative questions (local or live base URL)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_inquiry_beta_qa_smoke_v1_latest.json"

DEFAULT_QUESTIONS = [
    "욥기 고난과 의의 문제 — 학파별 해석 차이는 무엇인가?",
    "이사야 6장 부르심 — 학파·맥락 분기를 citation lock으로 정리해 달라",
    "시편 23편 — lemma·경로 관점에서 연구 질문을 구체화해 달라",
    "창세기 1장 1절 — 원어·게마트리아 관점에서 연구 질문을 제안해 달라",
    "요한복음 3장 16절 — 학파별 해석 분기를 비교해 달라",
    "로마서 8장 28절 — 고난·섭리 서사에서 citation lock 앵커는?",
    "출애굽기 3장 모세의 부르심 — 맥락 분기 요약",
    "잠언 3장 5절 — 지혜 문학과 신학적 해석 차이",
    "에베소서 2장 8절 — 은혜와 행위 논쟁 학파 분기",
    "요엘 2장 28절 — 성령·종말 해석의 학파 비교",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_inquiry(base: str, query: str, *, timeout: float) -> dict:
    url = f"{base.rstrip('/')}/api/logos-research/query"
    body = json.dumps(
        {
            "query": query,
            "output_format": "inquiry_report_v1",
            "domain_lane": "logos",
            "intent_chip": "reports",
            "stream_s4": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MKM-LogosInquirySmoke/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _validate_report(doc: dict) -> list[str]:
    errs: list[str] = []
    if not doc.get("ok"):
        errs.append(f"ok_false:{doc.get('error')}")
        return errs
    report = doc.get("report") or {}
    if report.get("schema") != "logos_inquiry_report_v1":
        errs.append("bad_report_schema")
    sections = report.get("sections") or {}
    s2 = sections.get("S2") or {}
    s3 = sections.get("S3") or {}
    s4 = sections.get("S4") or {}
    if not s2.get("lemma_edges_sha256"):
        errs.append("s2_missing_lemma_sha")
    if not s2.get("manifest_sha256"):
        errs.append("s2_missing_manifest_sha")
    if not (s4.get("body_ko") or "").strip():
        errs.append("s4_empty_body")
    if not isinstance(s3.get("groups"), list):
        errs.append("s3_groups_not_list")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://127.0.0.1:3010", help="no1kmedi origin")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--max", type=int, default=10)
    args = ap.parse_args()

    results: list[dict] = []
    errors: list[str] = []

    for q in DEFAULT_QUESTIONS[: max(1, args.max)]:
        row: dict = {"query": q, "ok": False, "errors": []}
        try:
            doc = _post_inquiry(args.base, q, timeout=args.timeout)
            row["http_ok"] = True
            row["errors"] = _validate_report(doc)
            row["ok"] = not row["errors"]
            if row["ok"]:
                report = doc["report"]
                row["preset_id"] = report.get("preset_id")
                row["s2_manifest_sha256"] = (report.get("sections") or {}).get("S2", {}).get(
                    "manifest_sha256"
                )
                row["s4_len"] = len(
                    ((report.get("sections") or {}).get("S4") or {}).get("body_ko") or ""
                )
                row["s3_group_count"] = len(
                    ((report.get("sections") or {}).get("S3") or {}).get("groups") or []
                )
            else:
                errors.append(f"{q[:24]}…:{','.join(row['errors'])}")
        except urllib.error.HTTPError as exc:
            row["http_ok"] = False
            row["http_code"] = exc.code
            try:
                row["body"] = json.loads(exc.read().decode("utf-8"))
            except Exception:
                row["body"] = None
            row["errors"] = [f"http_{exc.code}"]
            errors.append(f"{q[:24]}…:http_{exc.code}")
        except Exception as exc:  # noqa: BLE001
            row["errors"] = [str(exc)[:120]]
            errors.append(f"{q[:24]}…:{exc}")
        results.append(row)

    ok_count = sum(1 for r in results if r.get("ok"))
    report = {
        "schema": "logos_inquiry_beta_qa_smoke_v1",
        "ok": ok_count == len(results) and not errors,
        "generated_at_utc": _utc(),
        "base": args.base.rstrip("/"),
        "question_count": len(results),
        "ok_count": ok_count,
        "errors": errors,
        "results": results,
        "reproduce": f"py scripts/smoke_logos_inquiry_beta_qa_v1.py --base {args.base}",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "ok_count": ok_count, "out": str(OUT)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
