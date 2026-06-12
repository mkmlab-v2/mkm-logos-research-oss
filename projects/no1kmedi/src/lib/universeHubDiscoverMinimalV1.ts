/** Hub light chrome + discover centering (visual only; router unchanged). */

export function isHubLightChrome(pathname: string): boolean {
  const path = pathname.replace(/\/$/, "") || "/hub";
  return path === "/hub" || path.startsWith("/hub/");
}

/** /hub home only — centered one-question discover layout. */
export function isHubDiscoverMinimalMode(pathname: string): boolean {
  const path = pathname.replace(/\/$/, "") || "/hub";
  return path === "/hub";
}
