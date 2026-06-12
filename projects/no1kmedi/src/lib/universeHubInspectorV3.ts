/** Hub UI Chassis v3 — inspector visibility (deterministic, no LLM). */

export function shouldShowHubInspectorV3(pathname: string): boolean {
  const path = pathname.replace(/\/$/, "") || "/hub";
  return path === "/hub" || path.startsWith("/hub/logos");
}
