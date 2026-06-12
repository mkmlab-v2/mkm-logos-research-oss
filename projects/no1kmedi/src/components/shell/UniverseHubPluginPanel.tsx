import type { UniverseHubPluginId } from "@/lib/universeHubPluginsV2";
import {
  UniverseHubSpokeHeroV2,
  type HubSpokeCta,
} from "@/components/shell/UniverseHubSpokeHeroV2";

type Props = {
  pluginId: UniverseHubPluginId;
  title: string;
  body: string;
  primaryCta: HubSpokeCta;
  secondaryCta?: HubSpokeCta;
  phaseNote?: string;
};

export function UniverseHubPluginPanel({
  pluginId,
  title,
  body,
  primaryCta,
  secondaryCta,
  phaseNote,
}: Props) {
  return (
    <section className="universe-hub-spoke-panel" aria-labelledby={`hub-plugin-${pluginId}`}>
      <UniverseHubSpokeHeroV2
        pluginId={pluginId}
        titleId={`hub-plugin-${pluginId}`}
        title={title}
        body={body}
        primaryCta={primaryCta}
        secondaryCta={secondaryCta}
      />
      <p className="universe-hub-spoke-disclaimer">
        [HYPO] research_only · 백엔드 레인 자동 합선 없음
        {phaseNote ? ` · ${phaseNote}` : ""}
      </p>
    </section>
  );
}
