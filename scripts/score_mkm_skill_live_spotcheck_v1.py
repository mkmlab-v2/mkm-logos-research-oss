from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "mkm_skill_live_spotcheck_results_v1"
DEFAULT_INPUT = "docs/final/artifacts/skill_live_spotcheck_results_latest.json"
DEFAULT_OUTPUT = "docs/final/artifacts/skill_live_spotcheck_score_latest.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Score filled MKM live skill spot-check results.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--input-json", default=DEFAULT_INPUT)
    p.add_argument("--output-json", default=DEFAULT_OUTPUT)
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when live recall / negative accuracy below thresholds",
    )
    p.add_argument(
        "--allow-stub",
        action="store_true",
        help="Allow PASS without run_provenance=live (pytest/CI only)",
    )
    p.add_argument(
        "--allow-heuristic",
        action="store_true",
        help="Allow PASS with run_provenance=heuristic_auto (auto spot-check script)",
    )
    return p.parse_args()


def _coerce_pass(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "1", "pass"):
            return True
        if lowered in ("false", "no", "0", "fail"):
            return False
    return None


def score_rows(rows: list[dict]) -> dict:
    positive = [r for r in rows if r["kind"] in ("positive", "conflict")]
    negative = [r for r in rows if r["kind"] == "negative"]
    pending = [r for r in rows if _coerce_pass(r.get("pass")) is None]

    pos_pass = sum(1 for r in positive if _coerce_pass(r.get("pass")) is True)
    neg_pass = sum(1 for r in negative if _coerce_pass(r.get("pass")) is True)

    recall = pos_pass / len(positive) if positive else 1.0
    neg_accuracy = neg_pass / len(negative) if negative else 1.0

    failures = [r for r in rows if _coerce_pass(r.get("pass")) is False]

    return {
        "cases_total": len(rows),
        "pending": len(pending),
        "positive": {
            "total": len(positive),
            "pass": pos_pass,
            "live_recall": round(recall, 4),
        },
        "negative": {
            "total": len(negative),
            "pass": neg_pass,
            "negative_accuracy": round(neg_accuracy, 4),
        },
        "failures": failures,
        "pending_rows": [r["id"] for r in pending],
    }


def _provenance_label(doc: dict, rows: list[dict]) -> str:
    top = doc.get("run_provenance")
    if top == "live":
        return "live"
    if top == "heuristic_auto":
        return "heuristic_auto"
    if top == "stub":
        return "stub"
    if rows and all(str(row.get("chat_session", "")).strip() for row in rows):
        if all(row.get("run_provenance") == "heuristic_auto" for row in rows):
            return "heuristic_auto"
        if not any(str(row.get("chat_session", "")).startswith("auto-heuristic") for row in rows):
            return "live"
    return "stub_or_incomplete"


def check_thresholds(
    metrics: dict,
    thresholds: dict,
    *,
    provenance: str,
    allow_stub: bool,
    allow_heuristic: bool,
) -> list[str]:
    violations: list[str] = []
    if provenance == "live":
        pass
    elif provenance == "heuristic_auto" and allow_heuristic:
        pass
    elif provenance == "stub" and allow_stub:
        pass
    else:
        violations.append(
            "provenance_not_allowed:"
            f"{provenance} (live requires human chat; use --allow-heuristic for auto)"
        )
    if metrics["pending"] > 0:
        violations.append(f"pending_rows={metrics['pending']}")
    if metrics["positive"]["live_recall"] < thresholds.get("min_live_recall", 0.8):
        violations.append(
            "live_recall="
            f"{metrics['positive']['live_recall']}<{thresholds.get('min_live_recall', 0.8)}"
        )
    if metrics["negative"]["negative_accuracy"] < thresholds.get(
        "min_live_negative_accuracy", 0.75
    ):
        violations.append(
            "negative_accuracy="
            f"{metrics['negative']['negative_accuracy']}"
            f"<{thresholds.get('min_live_negative_accuracy', 0.75)}"
        )
    return violations


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    in_path = root / args.input_json
    out_path = root / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not in_path.is_file():
        payload = {
            "schema": SCHEMA,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
            "reason": "results_missing",
            "input": in_path.as_posix(),
            "hint": "py scripts/build_mkm_skill_live_spotcheck_v1.py then copy template to results path",
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"mkm_skill_live_spotcheck_score=ERROR results_missing input={in_path.as_posix()}")
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    rows = doc.get("rows", doc.get("cases", []))
    if not rows:
        print("mkm_skill_live_spotcheck_score=ERROR empty_rows")
        return 2

    thresholds = doc.get("thresholds", {"min_live_recall": 0.8, "min_live_negative_accuracy": 0.75})
    metrics = score_rows(rows)
    provenance_label = _provenance_label(doc, rows)
    violations = check_thresholds(
        metrics,
        thresholds,
        provenance=provenance_label,
        allow_stub=args.allow_stub,
        allow_heuristic=args.allow_heuristic,
    )
    ok = len(violations) == 0

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if ok else "FAIL",
        "ok": ok,
        "provenance": provenance_label,
        "live_provenance": provenance_label == "live",
        "violations": violations,
        "input": in_path.as_posix(),
        "thresholds": thresholds,
        "metrics": metrics,
        "reproducible_command": "py scripts/score_mkm_skill_live_spotcheck_v1.py --strict",
        "method": "Human spot-check in live Cursor chats; pass field required on every row.",
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "mkm_skill_live_spotcheck_score="
        f"{payload['status']} provenance={provenance_label} "
        f"live_recall={metrics['positive']['live_recall']} "
        f"neg_acc={metrics['negative']['negative_accuracy']} "
        f"pending={metrics['pending']} output={out_path.as_posix()}"
    )
    for row in metrics["failures"]:
        print(f"  fail {row['id']} expected={row['expected_skill']} observed={row.get('observed_skill')}")
    for v in violations:
        print(f"  violation: {v}")

    if args.strict and not ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
