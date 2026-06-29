#!/usr/bin/env python3
"""Export Han Vocology KM-VHI slice as OKF v0.1 bundle (B-track · portable)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

QUESTIONNAIRE = ROOT / "docs/final/artifacts/km_vhi_questionnaire_v0_1_latest.json"
APPENDIX = ROOT / "docs/research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md"
BUNDLE_ROOT = ROOT / "docs/final/artifacts/okf_bundles/han_vocology"
REPORT = ROOT / "docs/final/artifacts/han_vocology_okf_export_v1_latest.json"

from llm_wiki_okf_v1 import utc_now, wrap_concept_document  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _index_md(title: str, intro: str, children: list[tuple[str, str]], resource: str) -> str:
    links = "\n".join(f"- [{name}]({href})" for name, href in children)
    ts = utc_now()
    body = f"""# {title}

{intro}

## Concepts

{links}
"""
    return wrap_concept_document(
        body,
        {
            "schema": "okf_concept_v1",
            "type": "Playbook",
            "title": title,
            "description": intro.split("\n")[0][:200],
            "resource": resource,
            "tags": ["han-vocology", "B-track", "HYPO"],
            "timestamp": ts,
            "track": "B-track internal",
            "grade": "HYPO",
        },
    )


def path_relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _km_vhi_concept(q: dict[str, Any], ts: str) -> str:
    sections_md: list[str] = []
    for section in q.get("sections", []):
        sections_md.append(f"### {section.get('id')} — {section.get('name_ko', '')}")
        for item in section.get("items", []):
            sections_md.append(f"- **{item.get('id')}** {item.get('text_ko', '')}")

    scoring = q.get("scoring", {})
    interp = scoring.get("interpretation", [])
    interp_lines = "\n".join(
        f"| {row.get('range', '')} | {row.get('label_ko', '')} |" for row in interp
    )

    body = f"""# {q.get('full_name_ko', 'KM-VHI')}

> {q.get('disclaimer_ko', '')}

**Based on:** {q.get('based_on', 'VHI')}

## Sections

{chr(10).join(sections_md)}

## Scoring

| Range | Label |
|-------|-------|
{interp_lines}

**Clinical use (pilot):** {scoring.get('clinical_use', '')}

## SSOT

Machine-readable: [`km_vhi_questionnaire_v0_1_latest.json`](../../../km_vhi_questionnaire_v0_1_latest.json)

Human full appendix: [`HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md`](../../../../research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md)
"""
    rel = "instruments/km_vhi_v0_1.md"
    return wrap_concept_document(
        body,
        {
            "schema": "okf_concept_v1",
            "type": "Clinical Instrument",
            "title": q.get("full_name_ko", "KM-VHI"),
            "description": q.get("disclaimer_ko", ""),
            "resource": path_relative(QUESTIONNAIRE),
            "tags": ["han-vocology", "km-vhi", "clinical-instrument", "HYPO"],
            "timestamp": ts,
            "track": "B-track internal",
            "grade": "HYPO",
            "fact_lock": "Non-diagnostic self-report; not Track A or live clinical trigger",
        },
    )


def _appendix_concept(ts: str) -> str:
    excerpt = ""
    if APPENDIX.is_file():
        lines = APPENDIX.read_text(encoding="utf-8", errors="replace").splitlines()[:30]
        excerpt = "\n".join(lines)

    body = f"""# Han Vocology Appendix 6 — KM-VHI (full)

**Status:** `[B-track · 교육·실습용]`

Pointer to the full human-readable appendix in-repo. OKF bundle carries summary concepts only; SSOT JSON drives scoring automation.

## Excerpt (header)

```
{excerpt}
```

## Full document

[`docs/research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md`](../../../../research/HAN_VOCOLOGY_APPENDIX_6_KM_VHI_V0_1.md)
"""
    return wrap_concept_document(
        body,
        {
            "schema": "okf_concept_v1",
            "type": "Playbook",
            "title": "Han Vocology Appendix 6 — KM-VHI",
            "description": "Education appendix for KM-VHI questionnaire v0.1 (non-diagnostic).",
            "resource": path_relative(APPENDIX),
            "tags": ["han-vocology", "appendix", "education", "HYPO"],
            "timestamp": ts,
            "track": "B-track internal",
            "grade": "HYPO",
        },
    )


def _log_md(ts: str) -> str:
    body = f"""# Han Vocology OKF bundle log

| UTC | Event |
|-----|-------|
| {ts} | Initial export via `export_han_vocology_okf_bundle_v1.py` |
"""
    return wrap_concept_document(
        body,
        {
            "schema": "okf_concept_v1",
            "type": "Runbook",
            "title": "Han Vocology OKF changelog",
            "description": "Append-only export history for OKF bundle.",
            "resource": path_relative(BUNDLE_ROOT / "log.md"),
            "tags": ["han-vocology", "okf", "log"],
            "timestamp": ts,
        },
    )


def main() -> int:
    ts = utc_now()
    if not QUESTIONNAIRE.is_file():
        print(f"MISSING: {QUESTIONNAIRE}")
        return 1

    q = _load_json(QUESTIONNAIRE)

    paths_written: list[str] = []

    root_index = _index_md(
        "Han Vocology Knowledge Bundle",
        "B-track OKF v0.1 export for KM-VHI and education appendix pointers.",
        [
            ("KM-VHI Instrument", "instruments/km_vhi_v0_1.md"),
            ("Appendix 6 Playbook", "playbooks/appendix_6_km_vhi.md"),
        ],
        path_relative(BUNDLE_ROOT / "index.md"),
    )
    p = BUNDLE_ROOT / "index.md"
    _write(p, root_index)
    paths_written.append(path_relative(p))

    inst_index = _index_md(
        "Clinical Instruments",
        "Non-diagnostic questionnaires and rubrics.",
        [("KM-VHI v0.1", "km_vhi_v0_1.md")],
        path_relative(BUNDLE_ROOT / "instruments" / "index.md"),
    )
    p = BUNDLE_ROOT / "instruments" / "index.md"
    _write(p, inst_index)
    paths_written.append(path_relative(p))

    p = BUNDLE_ROOT / "instruments" / "km_vhi_v0_1.md"
    _write(p, _km_vhi_concept(q, ts))
    paths_written.append(path_relative(p))

    pb_index = _index_md(
        "Playbooks",
        "Education and training markdown.",
        [("Appendix 6 — KM-VHI", "appendix_6_km_vhi.md")],
        path_relative(BUNDLE_ROOT / "playbooks" / "index.md"),
    )
    p = BUNDLE_ROOT / "playbooks" / "index.md"
    _write(p, pb_index)
    paths_written.append(path_relative(p))

    p = BUNDLE_ROOT / "playbooks" / "appendix_6_km_vhi.md"
    _write(p, _appendix_concept(ts))
    paths_written.append(path_relative(p))

    p = BUNDLE_ROOT / "log.md"
    _write(p, _log_md(ts))
    paths_written.append(path_relative(p))

    report = {
        "schema": "han_vocology_okf_export_v1",
        "generated_at_utc": ts,
        "ok": True,
        "bundle_root": path_relative(BUNDLE_ROOT),
        "concept_count": 5,
        "paths": paths_written,
        "ssot_questionnaire": path_relative(QUESTIONNAIRE),
        "reproducible_command": "py scripts/export_han_vocology_okf_bundle_v1.py",
        "boundary_ack": "[HYPO] OKF export — not Track A · not clinical diagnosis · not CENTRAL promotion",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
