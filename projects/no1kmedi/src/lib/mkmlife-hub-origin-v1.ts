/** Hub / clinician deep-links to mkmlife — prod default; local dev via NEXT_PUBLIC_MKMLIFE_ORIGIN. */

const MKMLIFE_ORIGIN_DEFAULT = "https://mkmlife.com";

function stripTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

export function resolveMkmlifeOrigin(): string {
  const raw = process.env.NEXT_PUBLIC_MKMLIFE_ORIGIN?.trim();
  return raw ? stripTrailingSlash(raw) : MKMLIFE_ORIGIN_DEFAULT;
}

export function resolveMkmlifeAskOneUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_MKMLIFE_ASK_ONE_URL?.trim();
  if (explicit) return stripTrailingSlash(explicit);
  return `${resolveMkmlifeOrigin()}/ask-one`;
}

export function resolveMkmlifeReportsUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_MKMLIFE_REPORTS_URL?.trim();
  if (explicit) return stripTrailingSlash(explicit);
  return `${resolveMkmlifeOrigin()}/my-reports`;
}

export function resolveMkmlifeNewsDeckUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_MKMLIFE_NEWS_DECK_URL?.trim();
  if (explicit) return stripTrailingSlash(explicit);
  return `${resolveMkmlifeOrigin()}/news-deck`;
}

export type UniverseHubMkmlifeDeepLinks = {
  mkmlifeHome: string;
  mkmlifeAskOne: string;
  mkmlifeReports: string;
  mkmlifeNewsDeck: string;
};

export function buildUniverseHubMkmlifeDeepLinks(): UniverseHubMkmlifeDeepLinks {
  const origin = resolveMkmlifeOrigin();
  return {
    mkmlifeHome: origin,
    mkmlifeAskOne: resolveMkmlifeAskOneUrl(),
    mkmlifeReports: resolveMkmlifeReportsUrl(),
    mkmlifeNewsDeck: resolveMkmlifeNewsDeckUrl(),
  };
}
