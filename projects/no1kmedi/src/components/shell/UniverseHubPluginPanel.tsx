import Link from "next/link";
import type { UniverseHubPluginId } from "@/lib/universeHubPluginsV2";
import { pluginById } from "@/lib/universeHubPluginsV2";

type Props = {
  pluginId: UniverseHubPluginId;
  title: string;
  body: string;
  primaryCta: { href: string; label: string; external?: boolean };
  secondaryCta?: { href: string; label: string; external?: boolean };
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
  const plugin = pluginById(pluginId);

  return (
    <section className="universe-hub-plugin-panel" aria-labelledby={`hub-plugin-${pluginId}`}>
      <h1 id={`hub-plugin-${pluginId}`} className="universe-hub-plugin-title">
        {title}
      </h1>
      {plugin?.laneNote ? <p className="universe-hub-plugin-lane">{plugin.laneNote}</p> : null}
      <p className="universe-hub-plugin-body">{body}</p>
      <div className="universe-hub-plugin-actions">
        {primaryCta.external ? (
          <a
            className="universe-hub-cta universe-hub-cta--primary"
            href={primaryCta.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {primaryCta.label}
          </a>
        ) : (
          <Link className="universe-hub-cta universe-hub-cta--primary" href={primaryCta.href}>
            {primaryCta.label}
          </Link>
        )}
        {secondaryCta ? (
          secondaryCta.external ? (
            <a
              className="universe-hub-cta universe-hub-cta--ghost"
              href={secondaryCta.href}
              target="_blank"
              rel="noopener noreferrer"
            >
              {secondaryCta.label}
            </a>
          ) : (
            <Link className="universe-hub-cta universe-hub-cta--ghost" href={secondaryCta.href}>
              {secondaryCta.label}
            </Link>
          )
        ) : null}
      </div>
      <p className="universe-hub-disclaimer">
        [HYPO] research_only · 백엔드 레인 자동 합선 없음
        {phaseNote ? ` · ${phaseNote}` : ""}
      </p>
    </section>
  );
}
