#!/usr/bin/env python3
"""Phase 3 smoke: NL theory notebook + acode router + promotion registry."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL_FILE = ROOT / "reports/notebooklm_theory_mathematization_notebook_url_v1.txt"
OUT = ROOT / "docs/final/artifacts/mkm_theory_mathematization_phase3_smoke_v1_latest.json"

SMOKE_QUESTIONS = [
    "75식 전부 Track A 프로덕션인가? 51 UNRECOVERED 남았나?",
    "dt/dx 통일장 완성 주장해도 되나?",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _notebook_id() -> str:
    url = URL_FILE.read_text(encoding="utf-8").strip()
    m = re.search(r"notebook/([0-9a-f-]{36})", url, re.I)
    if not m:
        raise SystemExit(f"bad url: {URL_FILE}")
    return m.group(1)


def _nl_query(nb: str, question: str) -> dict:
    r = subprocess.run(
        ["nlm", "notebook", "query", nb, question],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(r.stdout)
    except json.JSONDecodeError:
        payload = {"raw": (r.stdout or r.stderr)[-2000:]}
    answer = ""
    if isinstance(payload.get("value"), dict):
        answer = str(payload["value"].get("answer", ""))
    elif isinstance(payload, dict):
        answer = str(payload.get("answer", ""))
    return {
        "question": question,
        "exit_code": r.returncode,
        "answer_excerpt": answer[:600],
        "refuses_track_a": any(x in answer for x in ("아니", "금지", "불가", "FORBIDDEN")),
        "mentions_unrecovered_zero": "UNRECOVERED 0" in answer or "0" in answer and "UNRECOVERED" in answer,
    }


def main() -> int:
    ts = utc_now()
    doc: dict = {"schema": "mkm_theory_mathematization_phase3_smoke_v1", "generated_at_utc": ts, "checks": []}

    formulas_path = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
    formulas = json.loads(formulas_path.read_text(encoding="utf-8"))
    empty_expr = [f["slot"] for f in formulas["formulas"] if not f.get("formula")]
    doc["checks"].append(
        {
            "name": "formula_expr_coverage",
            "total": 75,
            "with_expr": int(formulas.get("documented_with_expr", 0)),
            "empty_slots": empty_expr,
            "ok": len(empty_expr) == 0,
        }
    )

    reg_path = ROOT / "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    doc["checks"].append(
        {
            "name": "promotion_registry",
            "promotion_to_a_track_allowed": reg.get("promotion_to_a_track_allowed"),
            "ok": reg.get("promotion_to_a_track_allowed") is False and len(reg.get("entries", [])) == 75,
        }
    )

    try:
        import importlib.util

        router_path = ROOT / "scripts/mkm12_acode_pack_router_v1.py"
        spec = importlib.util.spec_from_file_location("mkm12_acode_pack_router_v1", router_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {router_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        routes = mod.route_all_formula_slots()
        doc["checks"].append(
            {
                "name": "acode_router_75",
                "routes": len(routes),
                "ok": len(routes) == 75,
            }
        )
    except Exception as exc:  # noqa: BLE001
        doc["checks"].append({"name": "acode_router_75", "ok": False, "error": str(exc)})

    nb = _notebook_id()
    for q in SMOKE_QUESTIONS:
        doc["checks"].append(_nl_query(nb, q))

    doc["ok"] = all(
        c.get("ok", False)
        for c in doc["checks"]
        if c.get("name") in ("formula_expr_coverage", "promotion_registry", "acode_router_75")
    )
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(OUT), "ok": doc["ok"], "checks": len(doc["checks"])}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
