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
  const graphStudio = "graph_studio" in c && c.graph_studio ? c.graph_studio : null;
  const pilotStatus = "pilot_status" in c && c.pilot_status ? c.pilot_status : null;
  const landing = "landing" in c && c.landing ? c.landing : null;
  const graphEntry =
    graphStudio?.entry_url ??
    `/logos-research/studio?preset=${LOGOS_GRAPH_STUDIO_DEFAULT_PRESET}&autorun=1&demo=1`;
  const heroEmbed = "hero_embed" in c && c.hero_embed ? c.hero_embed : null;
  const studio = "studio" in c ? c.studio : null;
  const trust = "trust_surface" in c ? c.trust_surface : null;
  const pilotTier = c.tiers.items.find((tier) => tier.id === "pilot");

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
                  {studio?.hero_cta_primary ?? "연구 스튜디오 열기"}
                </a>
                <a className="lr-btn lr-btn-ghost" href={graphEntry}>
                  {c.hero.cta_secondary}
                </a>
              </div>
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

        <section id="value" className="lr-section" aria-labelledby="lr-value-title">
          <h2 id="lr-value-title">{landing?.value_title ?? "핵심 가치"}</h2>
          <p className="lr-section-lead">
            {landing?.value_lead ??
              graphStudio?.lead ??
              "프리셋 선택 → GraphRAG 경로 → citation lock 구절."}
          </p>
          {graphStudio && "bullets" in graphStudio && Array.isArray(graphStudio.bullets) ? (
            <ul className="lr-graph-bullets">
              {graphStudio.bullets.map((item: string) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          <div className="lr-hero-cta">
            <a className="lr-btn lr-btn-primary" href="/logos-research/studio">
              연구 스튜디오 시작
            </a>
            <a className="lr-btn lr-btn-ghost" href="/logos-research/docs/how-it-works">
              작동 방식 (Docs)
            </a>
          </div>
        </section>

        <section id="pilot" className="lr-section lr-section--alt" aria-labelledby="lr-pilot-title">
          <h2 id="lr-pilot-title">{landing?.pilot_title ?? "기관 파일럿"}</h2>
          <p className="lr-section-lead">
            {landing?.pilot_lead ?? pilotTier?.note ?? "맞춤 preset · private slice · SOW 협의."}
          </p>
          {pilotStatus ? (
            <p className="lr-pilot-banner" role="status">
              <span className="lr-pilot-badge">{pilotStatus.badge}</span>
              {pilotStatus.lead}
              {pilotStatus.send_gate ? ` · send_gate ${pilotStatus.send_gate}` : ""}
            </p>
          ) : null}
          {pilotTier ? (
            <div className="lr-tier-card lr-tier-card--pilot">
              <strong>{pilotTier.name}</strong>
              <span>{pilotTier.audience}</span>
              <p>{pilotTier.note}</p>
            </div>
          ) : null}
          <div className="lr-hero-cta" id="lead">
            <a className="lr-btn lr-btn-primary" href={mailHref}>
              {c.hero.cta_primary}
            </a>
            <a className="lr-btn lr-btn-ghost" href="/logos-research/docs/pilot-scope">
              파일럿 범위 (Docs)
            </a>
          </div>
        </section>

        <section id="architecture" className="lr-section" aria-labelledby="lr-arch-title">
          <h2 id="lr-arch-title">{landing?.architecture_title ?? "기술 아키텍처"}</h2>
          <p className="lr-section-lead">
            {landing?.architecture_lead ?? "Fact-Lock 스냅샷 · research_only · NON_GATING."}
          </p>
          <div className="lr-metrics-grid lr-metrics-grid--compact">
            <MetricCard
              label="Path verification"
              value={
                m.path_verification_pass_rate != null
                  ? `${(Number(m.path_verification_pass_rate) * 100).toFixed(1)}%`
                  : "—"
              }
            />
            <MetricCard label="GraphRAG organic" value={String(m.graphrag_seed_organic ?? "—")} />
            <MetricCard label="B2B structure map" value={String(m.b2b_structure_map_verdict ?? "—")} />
          </div>
          {metricsDoc?.generated_at_utc ? (
            <p className="lr-section-lead lr-metrics-ts">스냅샷 · {metricsDoc.generated_at_utc}</p>
          ) : null}
          <details className="lr-meta-arch">
            <summary>
              <span className="lr-meta-arch-badge">
                {graphStudio?.meta_arch?.badge ?? "[HYPO] · Cosmic Meta-Architecture"}
              </span>
            </summary>
            <div className="lr-meta-arch-body" role="note">
              <p>{graphStudio?.meta_arch?.body}</p>
            </div>
          </details>
          {trust ? (
            <div className="lr-trust-inline">
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
            </div>
          ) : null}
          <details className="lr-disclaimer-fold">
            <summary>{c.disclaimer.title}</summary>
            <ul className="lr-disclaimer-list">
              {c.disclaimer.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </details>
        </section>
      </main>
    </div>
  );
}
