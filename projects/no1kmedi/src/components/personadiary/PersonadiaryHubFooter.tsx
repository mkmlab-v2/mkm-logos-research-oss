import { HubDomainCrossLinks } from "@/components/HubDomainCrossLinks";
import { siteCopy } from "@/content/siteCopy";

/** Cross-product links only — no personadiary self-link; preview_only boundary. */
export const PERSONADIARY_HUB_FOOTER_KEYS = [
  "showroom_jemaai",
  "premium_mkmlife",
  "b2b_acodeai",
  "research_mkmlab",
] as const;

export function PersonadiaryHubFooter() {
  return (
    <div className="pd-hub-footer">
      <p className="pd-hub-footer-kicker">MKM 관련 제품 · 별도 도메인</p>
      <HubDomainCrossLinks
        hubLinks={siteCopy.hub_links}
        keys={PERSONADIARY_HUB_FOOTER_KEYS}
        ariaLabel="MKM 관련 도메인 안내"
        className="pd-hub-footer-links hub-cross-links"
      />
      <a
        className="pd-hub-pill-link pd-hub-pill-link--brand"
        href="https://jema-ai.com"
        target="_blank"
        rel="noopener noreferrer"
        title="AI 한의학 · 임상 지원 브랜드 허브"
      >
        JEMA AI 브랜드 허브
      </a>
      <p className="pd-hub-footer-note">
        각 링크는 독립 제품·면책 정책을 따릅니다. personadiary는 콘셉트 프리뷰이며
        mkmlife·jemaai와 API·데이터를 합치지 않습니다.
      </p>
    </div>
  );
}
