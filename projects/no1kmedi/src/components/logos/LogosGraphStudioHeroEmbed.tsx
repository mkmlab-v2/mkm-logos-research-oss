"use client";

import { useEffect, useState } from "react";

import { buildLogosGraphStudioEmbedUrl } from "@/lib/logosGraphStudioEmbed";

type Props = {
  title: string;
  fallbackHref: string;
  note?: string;
  className?: string;
};

export function LogosGraphStudioHeroEmbed({ title, fallbackHref, note, className }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      const rm = mq.matches;
      setReducedMotion(rm);
      setSrc(buildLogosGraphStudioEmbedUrl({ autoplay: !rm }));
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  return (
    <figure
      className={`lr-hero-embed-wrap ${className ?? ""}`}
      data-layer-b-embed="hero"
      data-logos-graph-studio-embed="1"
      aria-label="Graph Studio Layer B live demo"
    >
      <div className="lr-hero-embed-governance" role="note">
        <span>[HYPO]</span>
        <span>NON_GATING</span>
        <span>preset demo</span>
        {reducedMotion ? <span>reduced-motion</span> : null}
      </div>
      <div className="lr-hero-embed" aria-busy={src ? undefined : true}>
        {src ? (
          <iframe
            src={src}
            title={title}
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="fullscreen"
            data-embed-hero="1"
          />
        ) : (
          <p className="lr-hero-embed-placeholder">Graph Studio demo loading…</p>
        )}
        <noscript>
          <p className="lr-hero-embed-noscript">
            <a href={fallbackHref} rel="noopener noreferrer">
              Open Graph Studio demo (JavaScript required for embed)
            </a>
          </p>
        </noscript>
      </div>
      {note ? <figcaption className="lr-hero-embed-caption">{note}</figcaption> : null}
      <p className="lr-hero-embed-fallback">
        <a href={fallbackHref} rel="noopener noreferrer">
          Open full Graph Studio
        </a>
      </p>
    </figure>
  );
}
