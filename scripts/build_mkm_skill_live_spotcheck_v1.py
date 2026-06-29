from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "mkm_skill_live_spotcheck_v1"
DEFAULT_CONFIG = "docs/final/fixtures/mkm_skill_live_spotcheck_v1.json"
DEFAULT_TEMPLATE_JSON = "docs/final/artifacts/skill_live_spotcheck_template_latest.json"
DEFAULT_CHECKLIST_MD = "docs/final/artifacts/skill_live_spotcheck_checklist_latest.md"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build MKM live skill-routing spot-check template.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--output-json", default=DEFAULT_TEMPLATE_JSON)
    p.add_argument("--output-md", default=DEFAULT_CHECKLIST_MD)
    p.add_argument(
        "--reset-results",
        action="store_true",
        help="Also copy fresh template to skill_live_spotcheck_results_latest.json",
    )
    return p.parse_args()


def _case_map(eval_fixture: dict) -> dict[str, dict]:
    return {case["id"]: case for case in eval_fixture["cases"]}


def build_template(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    eval_path = root / config["source_fixture"]
    eval_fixture = json.loads(eval_path.read_text(encoding="utf-8"))
    cases_by_id = _case_map(eval_fixture)

    missing = [cid for cid in config["selected_case_ids"] if cid not in cases_by_id]
    if missing:
        raise ValueError(f"missing_case_ids:{','.join(missing)}")

    rows = []
    for case_id in config["selected_case_ids"]:
        src = cases_by_id[case_id]
        rows.append(
            {
                "id": case_id,
                "kind": src["kind"],
                "prompt": src["prompt"],
                "expected_skill": src["expected_skill"],
                "notes": src.get("notes"),
                "chat_session": "",
                "observed_skill": "",
                "pass": None,
                "observer_notes": "",
                "run_provenance": None,
            }
        )

    return {
        "schema": SCHEMA,
        "run_provenance": None,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": config["protocol"],
        "thresholds": config["thresholds"],
        "source_fixture": eval_path.as_posix(),
        "config": config_path.as_posix(),
        "rows": rows,
        "reproducible_command": "py scripts/build_mkm_skill_live_spotcheck_v1.py",
    }


def render_checklist_md(doc: dict) -> str:
    lines = [
        "# MKM Skill Live Spot-Check",
        "",
        f"Generated: `{doc['generated_at_utc']}`",
        "",
        "## Protocol",
        "",
    ]
    for key, value in doc["protocol"].items():
        lines.append(f"- **{key}**: {value}")
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "| id | kind | prompt | expected_skill | observed_skill | pass | notes |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in doc["rows"]:
        prompt = row["prompt"].replace("|", "\\|")
        lines.append(
            f"| {row['id']} | {row['kind']} | {prompt} | `{row['expected_skill']}` | | | |"
        )
    lines.extend(
        [
            "",
            "## After filling",
            "",
            "1. `py scripts/build_mkm_skill_live_spotcheck_v1.py --reset-results`",
            "2. Set top-level `run_provenance` to `live` and fill each row (`chat_session`, `observed_skill`, `pass`)",
            "3. Run:",
            "",
            "```powershell",
            "py scripts/score_mkm_skill_live_spotcheck_v1.py --strict",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    config_path = root / args.config
    out_json = root / args.output_json
    out_md = root / args.output_md

    if not config_path.is_file():
        print(f"mkm_skill_live_spotcheck_build=ERROR config_missing path={config_path.as_posix()}")
        return 2

    doc = build_template(root, config_path)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_checklist_md(doc), encoding="utf-8")

    if args.reset_results:
        results_path = root / "docs/final/artifacts/skill_live_spotcheck_results_latest.json"
        results_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  reset_results={results_path.as_posix()}")

    print(
        "mkm_skill_live_spotcheck_build=OK "
        f"rows={len(doc['rows'])} "
        f"json={out_json.as_posix()} md={out_md.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
