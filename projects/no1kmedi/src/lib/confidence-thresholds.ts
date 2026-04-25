export type ConfidenceThresholds = {
  high_min: number;
  medium_min: number;
};

const DEFAULT_THRESHOLDS: ConfidenceThresholds = {
  high_min: 0.8,
  medium_min: 0.5,
};

function toFiniteNumber(value: string | undefined, fallback: number): number {
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function getConfidenceThresholds(): ConfidenceThresholds {
  const highMin = toFiniteNumber(process.env.NEXT_PUBLIC_CDSS_CONFIDENCE_HIGH_MIN, DEFAULT_THRESHOLDS.high_min);
  const mediumMin = toFiniteNumber(process.env.NEXT_PUBLIC_CDSS_CONFIDENCE_MEDIUM_MIN, DEFAULT_THRESHOLDS.medium_min);

  // Keep the contract monotonic: high >= medium.
  if (highMin < mediumMin) {
    return DEFAULT_THRESHOLDS;
  }

  return {
    high_min: highMin,
    medium_min: mediumMin,
  };
}
