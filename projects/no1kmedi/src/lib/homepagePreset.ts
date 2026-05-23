/**
 * Homepage visual preset SSOT (jema-ai.com marketing surface).
 * Color/accent overrides: globals.css `.preset-*` classes.
 * Spacing/type scale (8pt): globals.css `MKM-DESIGN-SYSTEM-TOKEN-V1` — same for all presets.
 * Token names: src/lib/designTokens.ts
 */
export const DEFAULT_HOMEPAGE_PRESET = "stripe-linear" as const;

export const homepagePresetKeys = ["stripe-linear", "apple-notion"] as const;

export type HomepagePresetKey = (typeof homepagePresetKeys)[number];

export const homepagePresetClassMap: Record<HomepagePresetKey, string> = {
  "stripe-linear": "preset-stripe-linear",
  "apple-notion": "preset-apple-notion",
};

export function isHomepagePresetKey(value: string): value is HomepagePresetKey {
  return (homepagePresetKeys as readonly string[]).includes(value);
}

/** Default preset when `?preset=` is absent or invalid. */
export function resolveHomepagePresetClass(preset?: string | null): string {
  if (preset && isHomepagePresetKey(preset)) {
    return homepagePresetClassMap[preset];
  }
  return homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];
}
