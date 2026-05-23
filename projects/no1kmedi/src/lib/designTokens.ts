/**
 * MKM design token names (Layer A SSOT).
 * Values live in src/app/globals.css — do not duplicate hex/spacing here.
 * Figma Variables should align 1:1 with these keys.
 */
export const mkmSpaceTokens = [
  "space-xs",
  "space-sm",
  "space-md",
  "space-lg",
  "space-xl",
  "space-2xl",
] as const;

export const mkmTextTokens = [
  "text-xs",
  "text-sm",
  "text-base",
  "text-lg",
  "text-xl",
  "text-2xl",
  "text-3xl",
  "text-hero",
] as const;

export const mkmRadiusTokens = ["radius-sm", "radius-md", "radius-lg"] as const;

export type MkmSpaceToken = (typeof mkmSpaceTokens)[number];
export type MkmTextToken = (typeof mkmTextTokens)[number];

/** CSS var() helper for agents/codegen */
export function cssVar(token: string): string {
  return `var(--${token})`;
}
