/** Discover-only Perplexity-style minimal chrome (visual only; router unchanged). */

export function isHubDiscoverMinimalMode(pathname: string): boolean {
  const path = pathname.replace(/\/$/, "") || "/hub";
  return path === "/hub";
}
