import { LogosResearchInquiryBetaHome } from "@/components/logos-research/LogosResearchInquiryBetaHome";
import { LogosResearchSiteChrome } from "@/components/logos-research/LogosResearchSiteChrome";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];

/** Logos public beta landing — text Q&A first; Graph Studio demoted to optional link. */
export default function LogosResearchPage() {
  return (
    <div className={`${presetClass} logos-research-page logos-research-beta-page`}>
      <LogosResearchSiteChrome active="home" />
      <LogosResearchInquiryBetaHome />
    </div>
  );
}
