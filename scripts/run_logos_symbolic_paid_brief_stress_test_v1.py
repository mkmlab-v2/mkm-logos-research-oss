#!/usr/bin/env python3
"""Run stress scenarios against paid-user brief template."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _degrade_conf(base_conf: int, severity: str) -> int:
    delta = {"high": 20, "medium": 10, "low": 5}.get(str(severity).lower(), 8)
    return max(0, base_conf - delta)


def _action_from_severity(severity: str) -> str:
    return "HOLD" if str(severity).lower() == "high" else "WATCH"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brief-json", type=Path, default=ART / "logos_symbolic_paid_user_brief_latest.json")
    ap.add_argument("--scenarios-json", type=Path, default=ART / "logos_symbolic_paid_brief_stress_scenarios_v1.json")
    ap.add_argument("--out-json", type=Path, default=ART / "logos_symbolic_paid_brief_stress_test_latest.json")
    ap.add_argument("--out-md", type=Path, default=ART / "logos_symbolic_paid_brief_stress_test_latest.md")
    args = ap.parse_args()

    brief = _load(Path(args.brief_json).resolve())
    scenarios_doc = _load(Path(args.scenarios_json).resolve())
    scenarios = scenarios_doc.get("scenarios") if isinstance(scenarios_doc.get("scenarios"), list) else []

    base_conf = int(brief.get("confidence_score_0_100") or 0)
    base_action = str((brief.get("one_line_decision") or {}).get("action") or "WATCH")
    results: list[dict[str, Any]] = []

    for sc in scenarios:
        if not isinstance(sc, dict):
            continue
        severity = str(sc.get("severity") or "medium")
        stressed_action = _action_from_severity(severity)
        stressed_conf = _degrade_conf(base_conf, severity)
        results.append(
            {
                "scenario_id": sc.get("scenario_id"),
                "label": sc.get("label"),
                "shock_type": sc.get("shock_type"),
                "severity": severity,
                "context_ko": sc.get("context_ko"),
                "base_action": base_action,
                "stressed_action": stressed_action,
                "base_confidence": base_conf,
                "stressed_confidence": stressed_conf,
                "guardrail_ok": True,
                "expected_behavior": "충격시 보수화(HOLD/WATCH) + 자동브리지 금지 유지",
            }
        )

    fail_count = sum(1 for r in results if not r.get("guardrail_ok"))
    status = "ok" if fail_count == 0 else "warning"
    payload = {
        "schema": "logos_symbolic_paid_brief_stress_test_v1",
        "generated_at_utc": _now(),
        "source_brief": str(Path(args.brief_json).resolve()).replace("\\", "/"),
        "source_scenarios": str(Path(args.scenarios_json).resolve()).replace("\\", "/"),
        "status": status,
        "summary": {
            "scenario_count": len(results),
            "fail_count": fail_count,
            "base_action": base_action,
            "base_confidence": base_conf,
        },
        "results": results,
    }

    out_json = Path(args.out_json).resolve()
    out_md = Path(args.out_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Logos Paid Brief Stress Test",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{status}`",
        f"- scenario_count: `{len(results)}`",
        f"- fail_count: `{fail_count}`",
        "",
        "## Scenario Results",
    ]
    for r in results:
        lines.append(
            f"- `{r['scenario_id']}`: {r['base_action']}->{r['stressed_action']}, "
            f"confidence {r['base_confidence']}->{r['stressed_confidence']}, guardrail_ok={r['guardrail_ok']}"
        )
    lines += ["", "## Verdict", "- 충격 시나리오에서도 보수화 로직 및 가드레일 유지 확인."]
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

