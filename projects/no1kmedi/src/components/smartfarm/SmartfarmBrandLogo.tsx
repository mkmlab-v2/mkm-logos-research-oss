"use client";

import { useId } from "react";

type Props = {
  /** Header lockup (default) or compact footer */
  variant?: "header" | "compact";
  className?: string;
};

/** Inline brand mark — leaf · droplet · LoRa arcs (no raster asset). */
export function SmartfarmBrandLogo({ variant = "header", className = "" }: Props) {
  const uid = useId().replace(/:/g, "");
  const size = variant === "compact" ? 32 : 44;
  const bg = `sf-logo-bg-${uid}`;
  const ring = `sf-logo-ring-${uid}`;
  const leaf = `sf-logo-leaf-${uid}`;
  const drop = `sf-logo-drop-${uid}`;
  const glow = `sf-logo-glow-${uid}`;

  return (
    <svg
      className={`sf-brand-logo-svg ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 44 44"
      role="img"
      aria-label="MKM Agriculture IoT"
    >
      <defs>
        <linearGradient id={bg} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0f1a16" />
          <stop offset="100%" stopColor="#152820" />
        </linearGradient>
        <linearGradient id={ring} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#5ee89a" />
          <stop offset="45%" stopColor="#3ecf7a" />
          <stop offset="100%" stopColor="#d4a853" />
        </linearGradient>
        <linearGradient id={leaf} x1="30%" y1="0%" x2="70%" y2="100%">
          <stop offset="0%" stopColor="#7ef0a8" />
          <stop offset="100%" stopColor="#2da865" />
        </linearGradient>
        <linearGradient id={drop} x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#8ed4ff" />
          <stop offset="100%" stopColor="#3a8fd4" />
        </linearGradient>
        <filter id={glow} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="1.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect
        x="1"
        y="1"
        width="42"
        height="42"
        rx="12"
        fill={`url(#${bg})`}
        stroke={`url(#${ring})`}
        strokeWidth="1.5"
      />
      {/* LoRa signal arcs */}
      <g stroke="#3ecf7a" strokeWidth="1.35" strokeLinecap="round" fill="none" opacity="0.85">
        <path d="M8 28 Q14 20 22 22" />
        <path d="M6 30 Q14 18 24 21" opacity="0.55" />
        <path d="M10 26 Q16 22 20 23" opacity="0.35" />
      </g>
      {/* Stem */}
      <path
        d="M22 32 C22 28 21 24 22 20 C23 16 24 14 22 12"
        stroke="#2da865"
        strokeWidth="1.6"
        strokeLinecap="round"
        fill="none"
      />
      {/* Leaf */}
      <path
        d="M22 20 C16 18 14 12 18 10 C22 9 26 12 22 20 Z"
        fill={`url(#${leaf})`}
        filter={`url(#${glow})`}
      />
      <path
        d="M22 22 C28 21 31 15 27 12 C24 11 21 14 22 22 Z"
        fill={`url(#${leaf})`}
        opacity="0.72"
      />
      {/* Water droplet */}
      <path
        d="M30 14 C30 11.5 32 10 33.5 12 C35 14 33 17.5 31 19 C29 17.5 30 16 30 14 Z"
        fill={`url(#${drop})`}
      />
      {/* Sensor node */}
      <circle cx="14" cy="30" r="2.2" fill="#3ecf7a" opacity="0.9" />
      <circle cx="14" cy="30" r="4" fill="none" stroke="#3ecf7a" strokeWidth="0.8" opacity="0.35" />
    </svg>
  );
}
