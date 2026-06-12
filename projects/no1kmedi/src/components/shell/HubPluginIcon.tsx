import type { ReactNode } from "react";
import type { UniverseHubPluginId } from "@/lib/universeHubPluginsV2";

type IconProps = {
  className?: string;
  size?: number;
};

const defaults = { size: 20, className: "universe-hub-plugin-icon" };

function Svg({ size, className, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      className={className ?? defaults.className}
      width={size ?? defaults.size}
      height={size ?? defaults.size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function HubBrandMark({ size = 18, className }: IconProps) {
  return (
    <svg
      className={className ?? "universe-hub-brand-mark"}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="5" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="M9 7.5h6v2.25H12v7.25H9V7.5z"
        fill="currentColor"
      />
    </svg>
  );
}

export function HubPluginIcon({
  pluginId,
  size,
  className,
}: IconProps & { pluginId: UniverseHubPluginId }) {
  const p = { size, className };
  switch (pluginId) {
    case "discover":
      return (
        <Svg {...p}>
          <path
            d="M4 10.5L12 4l8 6.5V19a1 1 0 01-1 1h-5v-6H10v6H5a1 1 0 01-1-1v-8.5z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </Svg>
      );
    case "governed_customization":
      return (
        <Svg {...p}>
          <path
            d="M12 3l2.2 4.5 5 .7-3.6 3.5.85 5L12 14.9 7.55 16.7l.85-5L4.8 8.2l5-.7L12 3z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </Svg>
      );
    case "a_code_sandbox":
      return (
        <Svg {...p}>
          <path
            d="M8 8l-4 4 4 4M16 8l4 4-4 4M14 6l-4 12"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </Svg>
      );
    case "compression_sandbox":
      return (
        <Svg {...p}>
          <path
            d="M7 10h10M12 6v12M8 14l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </Svg>
      );
    case "oracle_observatory":
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.75" />
          <circle cx="12" cy="12" r="2.5" fill="currentColor" />
        </Svg>
      );
    case "logos_observatory":
      return (
        <Svg {...p}>
          <path
            d="M12 3l2.4 5.5 6 .5-4.5 4 1.4 5.8L12 15.8 6.7 18.8 8.1 13 3.6 9l6-.5L12 3z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </Svg>
      );
    case "mkm_life":
      return (
        <Svg {...p}>
          <path
            d="M12 20s-6.5-4.2-6.5-9a4.5 4.5 0 019 0c0 4.8-6.5 9-6.5 9z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
        </Svg>
      );
    case "personadiary_preview":
      return (
        <Svg {...p}>
          <path
            d="M7 4h10a2 2 0 012 2v14l-4-2.5L11 20V6a2 2 0 00-2-2z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
          <path
            d="M9 8h6M9 11h4"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </Svg>
      );
    case "my_reports":
      return (
        <Svg {...p}>
          <rect x="5" y="4" width="14" height="16" rx="2" stroke="currentColor" strokeWidth="1.75" />
          <path d="M8 9h8M8 13h8M8 17h5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </Svg>
      );
    case "showroom":
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="1.75" />
          <path d="M12 8v8M8 12h8" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </Svg>
      );
    case "clinician":
      return (
        <Svg {...p}>
          <path
            d="M12 6v12M6 12h12"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </Svg>
      );
    case "operator_wtt":
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.75" />
          <path
            d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4l1.4-1.4M17 7l1.4-1.4"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </Svg>
      );
    default:
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="7" stroke="currentColor" strokeWidth="1.75" />
        </Svg>
      );
  }
}
