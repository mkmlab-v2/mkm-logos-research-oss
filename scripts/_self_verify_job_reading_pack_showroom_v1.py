"""One-shot self-verify for Job Reading Pack showroom slice (exit 0 = pass)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"

from scripts.showroom_public_export_guard_v1 import scan_forbidden  # noqa: E402


def main() -> int:
    checks: list[tuple[str, bool]] = []

    vc = json.loads(
        (ROOT / "reports/logos_job_reading_pack_verify_chain_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    checks.append(("verify_chain_ok", vc.get("ok") is True and vc.get("send_gate") == "HOLD"))

    slice_path = ROOT / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"
    doc = json.loads(slice_path.read_text(encoding="utf-8"))
    forbidden = scan_forbidden(doc)
    checks.append(("slice_no_forbidden", len(forbidden) == 0))
    checks.append(("why_false", doc.get("why_question_assembled") is False))
    checks.append(("packs_3", len(doc.get("reading_packs", [])) == 3))
    checks.append(
        (
            "export_gate_ok",
            doc.get("export_gate", {}).get("reading_pack_verify_ok") is True,
        )
    )
    sanitize_ok = True
    for p in doc["reading_packs"]:
        ex = p.get("card_excerpt_ko", "")
        if "docs/research/" in ex or "scripts/" in ex:
            sanitize_ok = False
            break
    checks.append(("sanitize_excerpts", sanitize_ok))

    qa = json.loads(
        (MVP / "showroom_meaning_topology_qa_presets_v1.json").read_text(encoding="utf-8")
    )
    job = [p for p in qa["presets"] if p.get("job_reading_pack_url")]
    checks.append(("qa_job_presets", len(job) >= 2))
    checks.append(("qa_disclaimer", qa.get("disclaimer", {}).get("no_trade_signals") is True))

    for name in (
        "public_showroom_logos_job_reading_pack_v1.html",
        "showroom_logos_job_reading_pack_slice_v1.json",
        "public_showroom_meaning_topology_qa_v2.html",
    ):
        checks.append((f"file_{name}", (MVP / name).is_file()))

    html_graph = (MVP / "public_showroom_meaning_topology_graph_v1.html").read_text(
        encoding="utf-8"
    )
    html_qa = (MVP / "public_showroom_meaning_topology_qa_v2.html").read_text(encoding="utf-8")
    html_job = (MVP / "public_showroom_logos_job_reading_pack_v1.html").read_text(encoding="utf-8")
    checks.append(("graph_link_job", "public_showroom_logos_job_reading_pack_v1.html" in html_graph))
    checks.append(("qa_link_job", "public_showroom_logos_job_reading_pack_v1.html" in html_qa))
    checks.append(("qa_job_cta", "job_reading_pack_url" in html_qa))
    checks.append(("qa_cite_ref_click", "cite-ref" in html_qa and "applyFocusNodes" in html_qa))
    checks.append(("qa_path_chips", "path-chip" in html_qa))
    checks.append(("qa_insight_panel", "insightPanel" in html_qa and "showInsightPanel" in html_qa))
    checks.append(("qa_b2b_demo_hero", "b2bDemoHero" in html_qa and "citation lock" in html_qa))
    checks.append(("qa_cold_start_boot", "beginColdStart" in html_qa and "B2B_PRESET_BOOTSTRAP" in html_qa))
    insight_cards = MVP / "showroom_qa_node_insight_cards_v1.json"
    checks.append(("file_insight_cards", insight_cards.is_file()))
    if insight_cards.is_file():
        ic = json.loads(insight_cards.read_text(encoding="utf-8"))
        checks.append(("insight_cards_job_anchor", "showroom_job_verse::Job.1.6" in (ic.get("cards") or {})))
        checks.append(("insight_cards_psalm_anchor", "showroom_psalm_verse::Ps.27.14" in (ic.get("cards") or {})))
        checks.append(("insight_cards_psalm_theme", "theme::hope_endurance_psalm" in (ic.get("cards") or {})))
    slice_graph = MVP / "showroom_meaning_topology_graph_slice_v1.json"
    if slice_graph.is_file():
        sg = json.loads(slice_graph.read_text(encoding="utf-8"))
        ps_refs = {str(n.get("ref")) for n in sg.get("nodes") or [] if str(n.get("ref", "")).startswith("Ps.")}
        checks.append(("slice_psalm_refs", len(ps_refs) >= 3))
    checks.append(
        ("job_loads_slice", "showroom_logos_job_reading_pack_slice_v1.json" in html_job)
    )
    checks.append(
        (
            "job_link_cosmic_code",
            "public_showroom_logos_job_cosmic_code_v1.html" in html_job,
        )
    )

    checks.append(
        (
            "job_qa_preset_deeplink",
            "preset=job_job_suffering_reason" in html_job,
        )
    )

    cosmic_path = MVP / "public_showroom_logos_job_cosmic_code_v1.html"
    checks.append(("file_public_showroom_logos_job_cosmic_code_v1.html", cosmic_path.is_file()))
    if cosmic_path.is_file():
        html_cosmic = cosmic_path.read_text(encoding="utf-8")
        checks.append(("cosmic_chapter_slider", "jobChapterSlider" in html_cosmic))
        checks.append(
            (
                "cosmic_backlink_reading_pack",
                "public_showroom_logos_job_reading_pack_v1.html" in html_cosmic,
            )
        )
        checks.append(
            (
                "cosmic_qa_preset_links",
                "preset=job_job_suffering_reason" in html_cosmic
                and "preset=job_existential_suffering" in html_cosmic,
            )
        )

    checks.append(
        (
            "commercial_primary_logos",
            json.loads(
                (
                    ROOT / "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json"
                ).read_text(encoding="utf-8")
            )
            .get("commercial_workspace", {})
            .get("product_primary_url")
            == "https://logos.jema-ai.com",
        )
    )

    readiness_path = ROOT / "reports/logos_observatory_commercial_readiness_v1_latest.json"
    if readiness_path.is_file():
        rd = json.loads(readiness_path.read_text(encoding="utf-8"))
        checks.append(
            ("readiness_product_primary", rd.get("product_primary_url") == "https://logos.jema-ai.com")
        )
        checks.append(
            ("readiness_demo_url", "meaning_topology_qa_v2" in str(rd.get("demo_url", "")))
        )

    deploy = (
        ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/deploy_showroom_static.ps1"
    ).read_text(encoding="utf-8")
    checks.append(("deploy_json", "showroom_logos_job_reading_pack_slice_v1.json" in deploy))
    checks.append(("deploy_html", "public_showroom_logos_job_reading_pack_v1.html" in deploy))
    checks.append(
        ("deploy_cosmic_html", "public_showroom_logos_job_cosmic_code_v1.html" in deploy)
    )
    checks.append(("job_footer_commercial_link", "logos.jema-ai.com" in html_job))
    fail = [name for name, ok in checks if not ok]
    print(f"SELF_VERIFY checks={len(checks)} pass={len(checks)-len(fail)} fail={len(fail)}")
    for name, ok in checks:
        print(("PASS" if ok else "FAIL"), name)
    if forbidden:
        print("FORBIDDEN hits:", forbidden[:5])
    if fail:
        return 1
    print("ALL_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
