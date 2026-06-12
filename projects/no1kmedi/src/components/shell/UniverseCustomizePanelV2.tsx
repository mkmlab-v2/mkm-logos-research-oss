import Link from "next/link";
import { HubSpokeDiagramV2 } from "@/components/shell/HubSpokeDiagramV2";
import { PackageLadderTableV2 } from "@/components/shell/PackageLadderTableV2";
import { UniverseHubSpokeHeroV2 } from "@/components/shell/UniverseHubSpokeHeroV2";
import {
  CUSTOMIZE_HEADLINE_KO,
  CUSTOMIZE_ICP_LABELS,
  CUSTOMIZE_PILLARS,
  CUSTOMIZE_SUBHEAD_KO,
} from "@/lib/universeHubCustomizeContentV2";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

export function UniverseCustomizePanelV2() {
  return (
    <article className="universe-hub-customize universe-hub-spoke-panel" aria-labelledby="hub-customize-title">
      <UniverseHubSpokeHeroV2
        pluginId="governed_customization"
        titleId="hub-customize-title"
        title={CUSTOMIZE_HEADLINE_KO}
        body={CUSTOMIZE_SUBHEAD_KO}
        primaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.enterpriseWttPersonaOs,
          label: "기업·파트너 소개",
        }}
        secondaryCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.compressionPilotApply,
          label: "토큰 압축 사전 감사 신청",
        }}
        extraCta={{
          href: UNIVERSE_HUB_DEEP_LINKS.wttPersonaOsDemo,
          label: "운영자 패널 데모 ↗",
          external: true,
        }}
      />

      <section className="universe-hub-customize-section" aria-labelledby="hub-spoke-heading">
        <h2 id="hub-spoke-heading" className="universe-hub-section-title">
          Hub–Spoke
        </h2>
        <p className="universe-hub-section-lead">단일 SKU 결합 없음 — 스포크는 선택 모듈입니다.</p>
        <HubSpokeDiagramV2 />
      </section>

      <section className="universe-hub-customize-section" aria-labelledby="hub-pillar-heading">
        <h2 id="hub-pillar-heading" className="universe-hub-section-title">
          3-Pillar 증거 축
        </h2>
        <ul className="universe-hub-pillar-strip">
          {CUSTOMIZE_PILLARS.map((p) => (
            <li key={p.id} className="universe-hub-pillar">
              <h3 className="universe-hub-pillar-title">{p.titleKo}</h3>
              <p className="universe-hub-pillar-summary">{p.summaryKo}</p>
              <Link className="universe-hub-pillar-cta" href={p.ctaHref}>
                {p.ctaLabelKo} →
              </Link>
              <code className="universe-hub-artifact-path" title="내부 SSOT 경로">
                {p.artifactPath}
              </code>
            </li>
          ))}
        </ul>
      </section>

      <section className="universe-hub-customize-section" aria-labelledby="hub-packages-heading">
        <h2 id="hub-packages-heading" className="universe-hub-section-title">
          패키지 라더
        </h2>
        <p className="universe-hub-section-lead">가격 미표기 · 상담·데모 전용 [DRAFT]</p>
        <PackageLadderTableV2 />
      </section>

      <section className="universe-hub-customize-section" aria-labelledby="hub-icp-heading">
        <h2 id="hub-icp-heading" className="universe-hub-section-title">
          ICP (90일)
        </h2>
        <ul className="universe-hub-icp-list">
          {CUSTOMIZE_ICP_LABELS.map((label) => (
            <li key={label}>
              <span className="universe-hub-icp-pill">{label}</span>
            </li>
          ))}
        </ul>
      </section>

      <footer className="universe-hub-compliance-footer">
        <span className="universe-hub-compliance-tag">[DRAFT]</span>
        <span className="universe-hub-compliance-tag">[HYPO]</span>
        <span className="universe-hub-compliance-tag universe-hub-compliance-tag--hold">SEND HOLD</span>
        <p>
          실고객 코퍼스 업로드·허브 채팅 합선·Track A KPI 대외 인용 금지 ·{" "}
          <a
            href="https://github.com/mkmlab-v2/mkm-destiny-ai-41e38ec6/blob/main/docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
            target="_blank"
            rel="noopener noreferrer"
          >
            PUBLIC_FACING 체크리스트 ↗
          </a>
        </p>
      </footer>
    </article>
  );
}
