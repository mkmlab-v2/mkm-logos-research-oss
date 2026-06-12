import Link from "next/link";
import type { UniverseHubPluginId } from "@/lib/universeHubPluginsV2";
import { pluginById } from "@/lib/universeHubPluginsV2";

export type HubSpokeCta = {
  href: string;
  label: string;
  external?: boolean;
};

type Props = {
  pluginId?: UniverseHubPluginId;
  titleId?: string;
  laneNote?: string;
  title: string;
  body: string;
  primaryCta?: HubSpokeCta;
  secondaryCta?: HubSpokeCta;
  extraCta?: HubSpokeCta;
};

function CtaButton({ cta, variant }: { cta: HubSpokeCta; variant: "primary" | "ghost" }) {
  const className = `universe-hub-cta universe-hub-cta--${variant}`;
  if (cta.external) {
    return (
      <a className={className} href={cta.href} target="_blank" rel="noopener noreferrer">
        {cta.label}
      </a>
    );
  }
  return (
    <Link className={className} href={cta.href}>
      {cta.label}
    </Link>
  );
}

export function UniverseHubSpokeHeroV2({
  pluginId,
  titleId,
  laneNote,
  title,
  body,
  primaryCta,
  secondaryCta,
  extraCta,
}: Props) {
  const plugin = pluginId ? pluginById(pluginId) : undefined;
  const lane = laneNote ?? plugin?.laneNote;

  return (
    <header className="universe-hub-spoke-hero">
      {lane ? <p className="universe-hub-spoke-lane">{lane}</p> : null}
      <h1 id={titleId} className="universe-hub-spoke-title">
        {title}
      </h1>
      <p className="universe-hub-spoke-body">{body}</p>
      {primaryCta || secondaryCta || extraCta ? (
        <div className="universe-hub-spoke-actions">
          {primaryCta ? <CtaButton cta={primaryCta} variant="primary" /> : null}
          {secondaryCta ? <CtaButton cta={secondaryCta} variant="ghost" /> : null}
          {extraCta ? <CtaButton cta={extraCta} variant="ghost" /> : null}
        </div>
      ) : null}
    </header>
  );
}
