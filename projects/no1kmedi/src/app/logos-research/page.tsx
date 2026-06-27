import { readFile } from "node:fs/promises";
import path from "node:path";

import { LogosResearchSiteChrome } from "@/components/logos-research/LogosResearchSiteChrome";
import { logosResearchCopy, type LogosResearchMetrics } from "@/content/logosResearchCopy";
import { LogosGraphStudioHeroInlineDemo } from "@/components/logos/LogosGraphStudioHeroInlineDemo";
import { LOGOS_GRAPH_STUDIO_DEFAULT_PRESET } from "@/lib/logosGraphStudioEmbed";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

const c = logosResearchCopy;
const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];

async function loadMetrics(): Promise<LogosResearchMetrics | null> {
  try {
    const filePath = path.join(process.cwd(), "public/data/logos_research_product_metrics_v1.json");
    const raw = await readFile(filePath, "utf8");
    return JSON.parse(raw) as LogosResearchMetrics;
  } catch {
    return null;
  }
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="lr-metric-card">
      <span className="lr-metric-label">{label}</span>
      <span className="lr-metric-value">{value}</span>
    </div>
  );
}

export default async function LogosResearchPage() {
  const metricsDoc = await loadMetrics();
  const m = metricsDoc?.metrics ?? {};
  const mailSubject = encodeURIComponent(c.contact.mail_subject);
  const mailHref = `mailto:${c.contact.email}?subject=${mailSubject}`;
  const demo = "demo_spine" in c && c.demo_spine ? c.demo_spine : null;
  const demoEntry = demo?.entry_url ?? c.footer.showroom;
  const demoLegacy =
    demo && "legacy_qa_v2_url" in demo && typeof demo.legacy_qa_v2_url === "string"
      ? demo.legacy_qa_v2_url
      : null;
  const demoJobPack = demo?.job_reading_pack_url ?? c.footer.job_reading_pack;
  const demoCosmic =
    demo && "job_cosmic_code_url" in demo && demo.job_cosmic_code_url
      ? demo.job_cosmic_code_url
      : "https://api.jemaai.cloud/public_showroom_logos_job_cosmic_code_v1.html";
  const graphStudio = "graph_studio" in c && c.graph_studio ? c.graph_studio : null;
  const pilotStatus = "pilot_status" in c && c.pilot_status ? c.pilot_status : null;
  const graphEntry =
    graphStudio?.entry_url ??
    `/logos-research/studio?preset=${LOGOS_GRAPH_STUDIO_DEFAULT_PRESET}&autorun=1&demo=1`;
  const graphLegacy =
    graphStudio && "legacy_qa_v2_url" in graphStudio && typeof graphStudio.legacy_qa_v2_url === "string"
      ? graphStudio.legacy_qa_v2_url
      : null;
  const heroEmbed = "hero_embed" in c && c.hero_embed ? c.hero_embed : null;

  const studio = "studio" in c ? c.studio : null;
  const trust = "trust_surface" in c ? c.trust_surface : null;

  return (
    <div className={`${presetClass} logos-research-page`}>
      <LogosResearchSiteChrome active="home" />

      <main id="main">
        <section className="lr-hero" aria-labelledby="lr-hero-title">
          <div className="lr-hero-grid">
            <div className="lr-hero-copy">
              <p className="lr-eyebrow">{c.hero.eyebrow}</p>
              <p className="lr-public-url">
                <span>Research</span>
                <a href={c.publicUrl}>{c.publicUrl.replace("https://", "")}</a>
              </p>
              <h1 id="lr-hero-title">
                {c.hero.title.split("\n").map((line, i) => (
                  <span key={line}>
                    {i > 0 ? <br /> : null}
                    {line}
                  </span>
                ))}
              </h1>
              <p className="lr-hero-lead">{c.hero.lead}</p>
              <div className="lr-hero-cta">
                <a className="lr-btn lr-btn-primary" href="/logos-research/studio">
                  {studio?.hero_cta_primary ?? "Open Graph Studio (on-domain)"}
                </a>
                <a className="lr-btn lr-btn-ghost" href={mailHref}>
                  {c.hero.cta_primary}
                </a>
                <a className="lr-btn lr-btn-ghost" href={graphEntry} rel="noopener noreferrer">
                  {c.hero.cta_secondary}
                </a>
              </div>
              {pilotStatus ? (
                <p className="lr-pilot-banner" role="status">
                  <span className="lr-pilot-badge">{pilotStatus.badge}</span>
                  {pilotStatus.lead}
                  {pilotStatus.send_gate ? ` · send_gate ${pilotStatus.send_gate}` : ""}
                </p>
              ) : null}
            </div>
            <LogosGraphStudioHeroInlineDemo
              title={heroEmbed?.title ?? "Logos Graph Studio — Layer B inline demo"}
              fallbackHref={graphEntry}
              note={
                heroEmbed?.note ??
                "질문 → 4슬롯 스토리보드 + 경로 마인드맵 미리보기 · citation lock · embed_demo (Track B [HYPO])"
              }
            />
          </div>
        </section>

        <section id="demo" className="lr-section lr-section--alt" aria-labelledby="lr-demo-title">
          <h2 id="lr-demo-title">{demo?.label ?? "Track C public demo"}</h2>
          <p className="lr-section-lead">
            {demo?.note ?? "Read-only demo on jemaai.cloud — not the commercial workspace."}
          </p>
          <div className="lr-hero-cta">
            <a className="lr-btn lr-btn-primary" href={demoEntry}>
              On-domain Studio (demo spine)
            </a>
            {demoLegacy ? (
              <a className="lr-btn lr-btn-ghost" href={demoLegacy} rel="noopener noreferrer">
                Legacy Q&amp;A (jemaai.cloud)
              </a>
            ) : null}
            <a className="lr-btn lr-btn-ghost" href={demoJobPack} rel="noopener noreferrer">
              Job Reading Pack (3-Pack)
            </a>
            <a className="lr-btn lr-btn-ghost" href={demoCosmic} rel="noopener noreferrer">
              Job Cosmic Code (OS·장별)
            </a>
          </div>
        </section>

        <section id="graph-studio" className="lr-section" aria-labelledby="lr-graph-title">
          <p className="lr-eyebrow">{graphStudio?.badge ?? "[HYPO] · research_only · NON_GATING"}</p>
          <h2 id="lr-graph-title">{graphStudio?.title ?? "Graph Studio"}</h2>
          <p className="lr-section-lead">
            {graphStudio?.lead ??
              "Question → GraphRAG path → subgraph highlight → citation-locked answer (Track C demo on jemaai.cloud)."}
          </p>
          {graphStudio && "bullets" in graphStudio && Array.isArray(graphStudio.bullets) ? (
            <ul className="lr-graph-bullets">
              {graphStudio.bullets.map((item: string) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          <p className="lr-section-lead lr-graph-studio-note">
            히어로는 <strong>인라인 스토리보드</strong>로 Job spine을 미리 보여줍니다 (iframe 없음).
            감사용 force-graph는 Studio 「감사 보기」탭에서 열 수 있습니다.
          </p>
          <div className="lr-hero-cta">
            <a className="lr-btn lr-btn-primary" href="/logos-research/studio">
              Open Graph Studio (on-domain)
            </a>
            {graphLegacy ? (
              <a className="lr-btn lr-btn-ghost" href={graphLegacy} rel="noopener noreferrer">
                Legacy demo (jemaai.cloud)
              </a>
            ) : null}
            <a
              className="lr-btn lr-btn-ghost"
              href={graphStudio?.job_pack_url ?? demoJobPack}
              rel="noopener noreferrer"
            >
              Job Reading Pack
            </a>
            <a
              className="lr-btn lr-btn-ghost"
              href={graphStudio?.job_cosmic_url ?? demoCosmic}
              rel="noopener noreferrer"
            >
              Job Cosmic Code
            </a>
          </div>
          <details className="lr-meta-arch">
            <summary>
              <span className="lr-meta-arch-badge">{graphStudio?.meta_arch?.badge ?? "[HYPO] · Cosmic Meta-Architecture"}</span>
            </summary>
            <div className="lr-meta-arch-body" role="note">
              <p>{graphStudio?.meta_arch?.body}</p>
            </div>
          </details>
        </section>

        <section id="metrics" className="lr-section lr-section--alt" aria-labelledby="lr-metrics-title">
          <h2 id="lr-metrics-title">{c.metrics_section?.title ?? "Fact-Lock metrics (live snapshot)"}</h2>
          <p className="lr-section-lead">
            {c.metrics_section?.lead ?? "아래 수치는 배포 시 동기화된 검증 스냅샷입니다. 마케팅 추정치가 아닙니다."}
            {metricsDoc?.generated_at_utc ? ` · ${metricsDoc.generated_at_utc}` : ""}
          </p>
          <div className="lr-metrics-grid">
            <MetricCard label="GraphRAG organic" value={String(m.graphrag_seed_organic ?? "—")} />
            <MetricCard label="Citation-valid themes" value={String(m.llm_citation_valid_themes ?? "—")} />
            <MetricCard label="Shared xref hubs" value={String(m.shared_hubs ?? "—")} />
            <MetricCard label="Insight units (Phase N)" value={String(m.insight_total_units ?? "—")} />
            <MetricCard label="Ledger records (Phase O)" value={String(m.ledger_records ?? "—")} />
            <MetricCard
              label="Path verification pass rate"
              value={
                m.path_verification_pass_rate != null
                  ? `${(Number(m.path_verification_pass_rate) * 100).toFixed(1)}%`
                  : "—"
              }
            />
            <MetricCard label="B2B structure map" value={String(m.b2b_structure_map_verdict ?? "—")} />
            <MetricCard
              label="Integration closure"
              value={m.integration_closure_ok === true ? "ok" : m.integration_closure_ok === false ? "fail" : "—"}
            />
          </div>
          {!metricsDoc ? (
            <p className="lr-missing">메트릭 스냅샷은 배포 시 동기화됩니다. (내부 빌드 파이프라인 · 경로 비공개)</p>
          ) : null}
        </section>

        <section id="tiers" className="lr-section" aria-labelledby="lr-tiers-title">
          <h2 id="lr-tiers-title">{c.tiers.title}</h2>
          <ul className="lr-tier-list">
            {c.tiers.items.map((tier) => (
              <li key={tier.id} className="lr-tier-card">
                <strong>{tier.name}</strong>
                <span>{tier.audience}</span>
                <p>{tier.note}</p>
              </li>
            ))}
          </ul>
        </section>

        <section id="disclaimer" className="lr-section lr-section--alt" aria-labelledby="lr-disclaimer-title">
          <h2 id="lr-disclaimer-title">{c.disclaimer.title}</h2>
          <ul className="lr-disclaimer-list">
            {c.disclaimer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        {trust ? (
          <section id="trust" className="lr-section lr-section--alt" aria-labelledby="lr-trust-title">
            <h2 id="lr-trust-title">{trust.title}</h2>
            <p className="lr-section-lead">{trust.lead}</p>
            <ul className="lr-trust-links">
              {trust.links.map((link: { label: string; href: string }) => (
                <li key={link.href}>
                  <a href={link.href} rel="noopener noreferrer">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
            <p className="lr-studio-bench-note">{trust.bench_note}</p>
          </section>
        ) : null}

        <section id="contact" className="lr-section" aria-labelledby="lr-contact-title">
          <h2 id="lr-contact-title">Pilot contact</h2>
          <p>
            <a className="lr-btn lr-btn-primary" href={mailHref}>
              {c.contact.email}
            </a>
          </p>
          <p className="lr-footer-links">
            <a href={c.footer.showroom}>{c.footer.showroom_label}</a>
            {"legacy_showroom" in c.footer && c.footer.legacy_showroom ? (
              <>
                {" · "}
                <a href={c.footer.legacy_showroom}>
                  {"legacy_showroom_label" in c.footer && c.footer.legacy_showroom_label
                    ? c.footer.legacy_showroom_label
                    : "Legacy demo"}
                </a>
              </>
            ) : null}
            {" · "}
            <a href={c.footer.job_reading_pack}>{c.footer.job_reading_pack_label}</a>
            {" · "}
            <a href={c.footer.hub}>{c.footer.hub_label}</a>
          </p>
        </section>
      </main>
    </div>
  );
}
