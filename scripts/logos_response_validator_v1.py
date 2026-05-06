#!/usr/bin/env python3
"""Validate logos_response_v1 JSON (schema + banned phrasing) and render Markdown brief.

Fact-Lock: structure via JSON Schema; deterministic-language ban on user-facing string fields only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "docs" / "final" / "artifacts" / "schemas"
DEFAULT_SCHEMA_V1 = SCHEMA_DIR / "logos_response_schema_v1.json"
DEFAULT_SCHEMA_V2 = SCHEMA_DIR / "logos_response_schema_v2.json"
# Backward-compatible alias (existing callers may import DEFAULT_SCHEMA).
DEFAULT_SCHEMA = DEFAULT_SCHEMA_V1
SCHEMA_BY_DOC_SCHEMA = {
    "logos_response_v1": DEFAULT_SCHEMA_V1,
    "logos_response_v2": DEFAULT_SCHEMA_V2,
}

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# Deterministic / hype phrasing (applied only to selected text fields, not keys).
BANNED_PATTERNS: list[str] = [
    r"100\s*%",
    r"무조건",
    r"반드시\s*상승",
    r"반드시\s*하락",
    r"확실히",
    r"절대적으로",
    r"보장(?:된다|합니다|됨)?",
    r"무조건\s*오른다",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _compile_banned() -> list[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in BANNED_PATTERNS]


def _extract_balanced_json_object(text: str) -> str | None:
    """First top-level `{ ... }` slice with string-aware brace counting."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def _extract_from_markdown_fence(text: str) -> str | None:
    m = _FENCE_RE.search(text)
    if not m:
        return None
    inner = m.group(1).strip()
    return inner if inner else None


def parse_llm_payload(text: str, *, strict: bool = False) -> dict[str, Any]:
    """Parse JSON object from raw LLM text (plain JSON, ```json fence, or first balanced object)."""
    s = text.strip()
    if not s:
        raise ValueError("empty_input")
    if strict:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            raise ValueError("root_must_be_object")
        return obj
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    fence = _extract_from_markdown_fence(s)
    if fence:
        try:
            obj = json.loads(fence)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    brace = _extract_balanced_json_object(s)
    if brace:
        obj = json.loads(brace)
        if isinstance(obj, dict):
            return obj
    raise ValueError("logos_json_extract_failed: no parseable object")


def find_banned_matches(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    found: list[str] = []
    for pat in patterns:
        if pat.search(text):
            found.append(pat.pattern)
    return found


def validate_banned(doc: dict[str, Any], patterns: list[re.Pattern[str]]) -> list[str]:
    errors: list[str] = []
    for field_label, text in [
        ("query_redefinition", str(doc.get("query_redefinition") or "")),
        ("final_insight_non_gating", str(doc.get("final_insight_non_gating") or "")),
    ]:
        for pat in patterns:
            if pat.search(text):
                errors.append(f"banned_phrase:{field_label}:{pat.pattern}")

    vec = doc.get("vector_4d") if isinstance(doc.get("vector_4d"), dict) else {}
    pd = str(vec.get("phase_description") or "")
    for pat in patterns:
        if pat.search(pd):
            errors.append(f"banned_phrase:vector_4d.phase_description:{pat.pattern}")

    anchors = doc.get("symbolic_anchors") or []
    for i, a in enumerate(anchors):
        if not isinstance(a, dict):
            continue
        for sub in ("motif", "core_meaning"):
            t = str(a.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:symbolic_anchors[{i}].{sub}:{pat.pattern}")

    gl = doc.get("gematria_layer")
    if isinstance(gl, dict) and gl.get("notes") is not None:
        notes = str(gl.get("notes") or "")
        for pat in patterns:
            if pat.search(notes):
                errors.append(f"banned_phrase:gematria_layer.notes:{pat.pattern}")

    rows = doc.get("chronicle_mapping") or []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        for sub in ("summary", "period_or_ref", "evidence_pointer"):
            t = str(row.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:chronicle_mapping[{i}].{sub}:{pat.pattern}")

    risks = doc.get("risk_and_falsification") or []
    for i, line in enumerate(risks):
        t = str(line or "")
        for pat in patterns:
            if pat.search(t):
                errors.append(f"banned_phrase:risk_and_falsification[{i}]:{pat.pattern}")

    denoms = doc.get("denominational_view") or []
    for i, row in enumerate(denoms):
        if not isinstance(row, dict):
            continue
        for sub in ("tradition_label", "interpretation_summary"):
            t = str(row.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:denominational_view[{i}].{sub}:{pat.pattern}")

    tcrit = doc.get("text_critical_notes")
    if isinstance(tcrit, dict):
        for sub in ("source_scope", "variant_notes", "uncertainty_notes"):
            t = str(tcrit.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:text_critical_notes.{sub}:{pat.pattern}")

    mkm_math = doc.get("mkm_interpretation_math")
    if isinstance(mkm_math, dict):
        t = str(mkm_math.get("commentary") or "")
        for pat in patterns:
            if pat.search(t):
                errors.append(f"banned_phrase:mkm_interpretation_math.commentary:{pat.pattern}")

    deep = doc.get("deep_logos_tension_gematria")
    if isinstance(deep, dict):
        for sub in ("pattern_id", "commentary"):
            t = str(deep.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:deep_logos_tension_gematria.{sub}:{pat.pattern}")
        fconds = deep.get("falsification_conditions") or []
        for i, line in enumerate(fconds):
            t = str(line or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:deep_logos_tension_gematria.falsification_conditions[{i}]:{pat.pattern}")

    arch = doc.get("archetypal_chaos_order_phase")
    if isinstance(arch, dict):
        for sub in ("phase_label", "narrative_claim"):
            t = str(arch.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:archetypal_chaos_order_phase.{sub}:{pat.pattern}")
        fconds = arch.get("falsification_conditions") or []
        for i, line in enumerate(fconds):
            t = str(line or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:archetypal_chaos_order_phase.falsification_conditions[{i}]:{pat.pattern}")

    morph = doc.get("morphology_layer")
    if isinstance(morph, dict):
        for sub in ("registry_id", "scope", "interpretation_guard"):
            t = str(morph.get(sub) or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:morphology_layer.{sub}:{pat.pattern}")
        for i, row in enumerate(morph.get("top_lemmas") or []):
            if not isinstance(row, dict):
                continue
            t = str(row.get("lemma") or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:morphology_layer.top_lemmas[{i}].lemma:{pat.pattern}")
        for i, row in enumerate(morph.get("top_morph_tags") or []):
            if not isinstance(row, dict):
                continue
            t = str(row.get("morph_tag") or "")
            for pat in patterns:
                if pat.search(t):
                    errors.append(f"banned_phrase:morphology_layer.top_morph_tags[{i}].morph_tag:{pat.pattern}")

    return errors


def validate_schema(doc: dict[str, Any], schema_path: Path) -> list[str]:
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        return ["jsonschema_missing: pip install jsonschema"]

    schema = _read_json(schema_path)
    validator = Draft7Validator(schema)
    return [f"schema:{e.message} ({'/'.join(str(x) for x in e.path)})" for e in validator.iter_errors(doc)]


def validate_all(doc: dict[str, Any], schema_path: Path) -> tuple[list[str], list[str]]:
    schema_errs = validate_schema(doc, schema_path)
    patterns = _compile_banned()
    ban_errs = validate_banned(doc, patterns) if not schema_errs else []
    return schema_errs, ban_errs


def resolve_schema_path(schema_arg: str, doc: dict[str, Any]) -> Path:
    if schema_arg:
        return Path(schema_arg).resolve()
    key = str(doc.get("schema") or "")
    return SCHEMA_BY_DOC_SCHEMA.get(key, DEFAULT_SCHEMA_V1).resolve()


def render_to_markdown(doc: dict[str, Any]) -> str:
    md: list[str] = []
    md.append("## 성경 고도화 해석 브리핑 (Fact-Lock · NON_GATING)")
    md.append("")
    md.append(f"- **schema**: `{doc.get('schema')}`")
    md.append(f"- **Corpus ID**: `{doc.get('corpus_profile_id')}`")
    md.append("")

    md.append("### 1) 질문 재정의")
    md.append(f"> {doc.get('query_redefinition')}")
    md.append("")

    md.append("### 2) 상징 앵커")
    for a in doc.get("symbolic_anchors") or []:
        if isinstance(a, dict):
            md.append(f"- **{a.get('motif')}**: {a.get('core_meaning')}")
    md.append("")

    gl = doc.get("gematria_layer") if isinstance(doc.get("gematria_layer"), dict) else {}
    md.append("### 3) 게마트리아·수리 패턴 (해석층)")
    md.append("```json")
    md.append(json.dumps(gl, ensure_ascii=False, indent=2))
    md.append("```")
    md.append("")

    vec = doc.get("vector_4d") if isinstance(doc.get("vector_4d"), dict) else {}
    md.append("### 4) 4D 수학화 (S/L/K/M)")
    md.append(
        f"- `S_spirit`: {vec.get('S_spirit')} | `L_logos`: {vec.get('L_logos')} | "
        f"`K_kairos`: {vec.get('K_kairos')} | `M_material`: {vec.get('M_material')}"
    )
    md.append(f"- **위상 해석**: {vec.get('phase_description')}")
    md.append("")

    md.append("### 5) 연대기·외부 매핑")
    for row in doc.get("chronicle_mapping") or []:
        if isinstance(row, dict):
            cb = row.get("confidence_band")
            extra = f" (confidence: `{cb}`)" if cb else ""
            md.append(
                f"- **{row.get('summary')}** — `{row.get('period_or_ref')}` → `{row.get('evidence_pointer')}`{extra}"
            )
    md.append("")

    md.append("### 6) 리스크·반증·한계")
    for risk in doc.get("risk_and_falsification") or []:
        md.append(f"- {risk}")
    md.append("")

    md.append("### 7) 최종 통찰 [NON_GATING]")
    md.append(str(doc.get("final_insight_non_gating") or ""))
    md.append("")
    return "\n".join(md)


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.input)
    doc = _read_json(path)
    schema_path = resolve_schema_path(str(args.schema or ""), doc)
    schema_errs, ban_errs = validate_all(doc, schema_path)
    if schema_errs:
        print("SCHEMA_FAIL", file=sys.stderr)
        for e in schema_errs:
            print(e, file=sys.stderr)
        return 1
    if ban_errs:
        print("BANNED_FAIL", file=sys.stderr)
        for e in ban_errs:
            print(e, file=sys.stderr)
        return 2
    print(f"OK: {doc.get('schema')} valid")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    path = Path(args.input)
    doc = _read_json(path)
    schema_path = resolve_schema_path(str(args.schema or ""), doc)
    schema_errs, ban_errs = validate_all(doc, schema_path)
    if schema_errs or ban_errs:
        if schema_errs:
            for e in schema_errs:
                print(e, file=sys.stderr)
        if ban_errs:
            for e in ban_errs:
                print(e, file=sys.stderr)
        return 1 if schema_errs else 2
    md = render_to_markdown(doc)
    out = Path(args.output) if args.output else None
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"WROTE: {out}")
    else:
        print(md)
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    raw = Path(args.input).read_text(encoding="utf-8")
    try:
        doc = parse_llm_payload(raw, strict=bool(args.strict_json))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"JSON_EXTRACT_FAIL: {exc}", file=sys.stderr)
        return 3
    if not isinstance(doc, dict):
        print("JSON_ROOT_MUST_BE_OBJECT", file=sys.stderr)
        return 3
    schema_path = resolve_schema_path(str(args.schema or ""), doc)
    schema_errs, ban_errs = validate_all(doc, schema_path)
    if schema_errs:
        for e in schema_errs:
            print(e, file=sys.stderr)
        return 1
    if ban_errs:
        for e in ban_errs:
            print(e, file=sys.stderr)
        return 2
    print(render_to_markdown(doc))
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    raw = Path(args.input).read_text(encoding="utf-8")
    try:
        doc = parse_llm_payload(raw, strict=bool(args.strict_json))
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"JSON_EXTRACT_FAIL: {exc}", file=sys.stderr)
        return 3
    out = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        op = Path(args.output)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(out, encoding="utf-8")
        print(f"WROTE: {op}")
    else:
        print(out, end="")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)

    sub = ap.add_subparsers(dest="cmd", required=True)

    schema_kw = {
        "default": "",
        "help": "Optional schema path. If omitted, auto-select by doc.schema (v1/v2).",
    }

    p_val = sub.add_parser("validate", help="Validate JSON file")
    p_val.add_argument("--schema", **schema_kw)
    p_val.add_argument("--input", "-i", required=True, help="Input JSON path")
    p_val.set_defaults(func=cmd_validate)

    p_ren = sub.add_parser("render", help="Validate then write Markdown")
    p_ren.add_argument("--schema", **schema_kw)
    p_ren.add_argument("--input", "-i", required=True)
    p_ren.add_argument("--output", "-o", default="", help="Output .md path (default: stdout)")
    p_ren.set_defaults(func=cmd_render)

    p_pipe = sub.add_parser(
        "pipeline",
        help="Parse LLM raw text (JSON or ```json fence or first {…} object), validate, print Markdown",
    )
    p_pipe.add_argument("--schema", **schema_kw)
    p_pipe.add_argument("--input", "-i", required=True, help="Path containing raw LLM output or JSON")
    p_pipe.add_argument(
        "--strict-json",
        action="store_true",
        help="Require file to be a single JSON object only (no fences / no prefix text)",
    )
    p_pipe.set_defaults(func=cmd_pipeline)

    p_ext = sub.add_parser("extract", help="Extract normalized JSON object to stdout or --output")
    p_ext.add_argument("--input", "-i", required=True)
    p_ext.add_argument("--output", "-o", default="", help="Write extracted JSON (optional)")
    p_ext.add_argument("--strict-json", action="store_true")
    p_ext.set_defaults(func=cmd_extract)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
