#!/usr/bin/env python3
"""Emit Track B policy chain readiness report (deterministic; no LLM).

Validates MKM theology baseline JSON, optional JSON Schema validation,
existence of provenance_slots paths, distill contract/schema,
LOGOS_VECTOR_INDEX_POLICY_V1 and corpus_alignment required_preconditions.
Exit 0 only when overall_ok.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_THEOLOGY = ROOT / "docs/final/artifacts/LOGOS_MKM_THEOLOGY_BASELINE_V1.json"
DEFAULT_THEOLOGY_SCHEMA = ROOT / "docs/final/schemas/logos_mkm_theology_baseline_v1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_b_policy_readiness_v1_latest.json"
DISTILL_CONTRACT = ROOT / "docs/final/artifacts/LOGOS_DEEP_RESEARCH_DISTILL_CONTRACT_V1.json"
DISTILL_SCHEMA = ROOT / "docs/final/schemas/logos_deep_research_distill_v1.schema.json"
DEFAULT_VECTOR_POLICY = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"

ARTIFACT_SCHEMA = "logos_track_b_policy_readiness_v1"
VERSION = "1.1.0"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theology-baseline", type=Path, default=DEFAULT_THEOLOGY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    checks: dict[str, Any] = {}
    failures: list[str] = []

    if not args.theology_baseline.is_file():
        checks["theology_baseline"] = {"exists": False, "path": _rel(args.theology_baseline)}
        doc_out: dict[str, Any] = {
            "schema": ARTIFACT_SCHEMA,
            "version": VERSION,
            "ts_utc": ts,
            "hypothesis_tier": "B",
            "overall_ok": False,
            "checks": checks,
            "failure_codes": ["theology_baseline_missing"],
            "notes": "theology baseline missing",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    raw_tb = json.loads(args.theology_baseline.read_text(encoding="utf-8"))
    checks["theology_baseline"] = {"exists": True, "path": _rel(args.theology_baseline)}
    if raw_tb.get("schema") != "logos_mkm_theology_baseline_v1":
        failures.append("theology_schema_field")
    gov = raw_tb.get("governance_and_reporting") or {}
    checks["governance_flags"] = {
        "not_a_deregulation_claim": gov.get("not_a_deregulation_claim") is True,
    }
    if gov.get("not_a_deregulation_claim") is not True:
        failures.append("governance_not_a_deregulation_claim")

    try:
        import jsonschema

        sch = json.loads(DEFAULT_THEOLOGY_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(sch).validate(raw_tb)
    except ImportError:
        checks["theology_jsonschema"] = "skipped_no_jsonschema"
    except Exception as e:
        checks["theology_jsonschema"] = f"fail:{e}"
        failures.append("theology_jsonschema")
    else:
        checks["theology_jsonschema"] = "ok"

    slots = raw_tb.get("provenance_slots") or {}
    path_checks: dict[str, Any] = {}
    if isinstance(slots, dict):
        for key, rel in slots.items():
            if not isinstance(rel, str) or not rel.strip():
                path_checks[key] = {"path": rel, "exists": False}
                failures.append(f"slot_empty:{key}")
                continue
            p = (ROOT / Path(rel)).resolve()
            ok = p.is_file()
            path_checks[key] = {"path": rel, "exists": ok}
            if not ok:
                failures.append(f"path_missing:{key}")
    checks["provenance_paths"] = path_checks

    distill_c_ok = DISTILL_CONTRACT.is_file()
    distill_s_ok = DISTILL_SCHEMA.is_file()
    checks["distill_contract"] = {"path": _rel(DISTILL_CONTRACT), "exists": distill_c_ok}
    checks["distill_schema"] = {"path": _rel(DISTILL_SCHEMA), "exists": distill_s_ok}
    if not distill_c_ok:
        failures.append("distill_contract")
    if not distill_s_ok:
        failures.append("distill_schema")

    if not DEFAULT_VECTOR_POLICY.is_file():
        checks["vector_policy"] = {"exists": False, "path": _rel(DEFAULT_VECTOR_POLICY)}
        failures.append("vector_policy_missing")
    else:
        try:
            vp = json.loads(DEFAULT_VECTOR_POLICY.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            checks["vector_policy"] = {"exists": True, "parse_error": str(e)}
            failures.append("vector_policy_json")
            vp = {}
        else:
            if vp.get("schema") != "logos_vector_index_policy_v1":
                failures.append("vector_policy_schema_field")
            cal = vp.get("corpus_alignment") or {}
            req_list = cal.get("required_preconditions")
            preconds: list[dict[str, Any]] = []
            if isinstance(req_list, list):
                for rel in req_list:
                    if not isinstance(rel, str) or not rel.strip():
                        failures.append("vector_precondition_invalid")
                        continue
                    p = (ROOT / Path(rel)).resolve()
                    ok = p.is_file()
                    preconds.append({"path": rel, "exists": ok})
                    if not ok:
                        failures.append(f"vector_precondition_missing:{rel}")
            checks["vector_policy"] = {
                "exists": True,
                "path": _rel(DEFAULT_VECTOR_POLICY),
                "status": vp.get("status"),
                "preconditions": preconds,
            }

    schema_gate = checks.get("theology_jsonschema") in ("ok", "skipped_no_jsonschema")
    paths_ok = bool(path_checks) and all(
        isinstance(v, dict) and v.get("exists") for v in path_checks.values()
    )

    overall = len(failures) == 0 and schema_gate and paths_ok

    doc_out = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "overall_ok": overall,
        "checks": checks,
        "failure_codes": failures,
        "notes": ""
        if overall
        else "see failure_codes; install jsonschema for full theology validation when possible",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
