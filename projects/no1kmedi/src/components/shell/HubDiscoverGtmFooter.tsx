import { HubDomainCrossLinks, HUB_FOOTER_KEYS } from "@/components/HubDomainCrossLinks";
import { JemaAiHubBrandHandoffStrip } from "@/components/shell/JemaAiHubBrandHandoffStrip";
import { siteCopy } from "@/content/siteCopy";

/** SSR portfolio CTA + positioning strip for /hub (MKM_DOMAIN_PORTFOLIO §1.1b). */
export function HubDiscoverGtmFooter() {
  const positioning = siteCopy.positioning_v1?.footer_strip_ko;

  return (
    <div className="hub-discover-gtm-footer">
      <JemaAiHubBrandHandoffStrip locale="ko" />
      {positioning ? (
        <p className="universe-hub-positioning-strip hub-discover-gtm-positioning" role="note">
          {positioning}
        </p>
      ) : null}
      <details className="hub-discover-gtm-links-folded">
        <summary>MKM Ecosystem 안내</summary>
        <HubDomainCrossLinks
          hubLinks={siteCopy.hub_links}
          keys={HUB_FOOTER_KEYS}
          className="hub-cross-links hub-discover-gtm-links"
          ariaLabel="MKM 관련 도메인 안내"
        />
      </details>
    </div>
  );
}
