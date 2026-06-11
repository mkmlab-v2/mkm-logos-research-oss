"use client";

import { useEffect, useRef } from "react";

import {
  initShatterParticles,
  stepShatterParticles,
  type LatticePhase,
  type MatchedHub,
} from "@/lib/personadiaryLatticeConvergenceV1";

const KIND_DOT: Record<string, string> = {
  theme: "#ffd60a",
  concept: "#64d2ff",
  regime: "#5e5ce6",
  verse: "#94a3b8",
  lemma: "#bf5af2",
  other: "#a78bfa",
};

type Props = {
  size: number;
  phase: LatticePhase;
  tokens: string[];
  matchedHubs: MatchedHub[];
  convergePct: number;
};

export function PersonadiaryLatticeOverlay({
  size,
  phase,
  tokens,
  matchedHubs,
  convergePct,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<ReturnType<typeof initShatterParticles>>([]);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    if (phase === "shatter" && tokens.length) {
      const cx = size / 2;
      const cy = size / 2;
      particlesRef.current = initShatterParticles(tokens, cx, cy, size * 0.38);
    }
  }, [phase, tokens, size]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const cx = size / 2;
    const cy = size / 2;

    const draw = () => {
      ctx.clearRect(0, 0, size, size);

      if (phase === "shatter" || phase === "vortex") {
        const mode = phase === "vortex" ? "vortex" : "shatter";
        particlesRef.current = stepShatterParticles(particlesRef.current, cx, cy, mode);
        for (const p of particlesRef.current) {
          ctx.globalAlpha = Math.min(1, p.life);
          ctx.fillStyle = "rgba(196, 181, 253, 0.92)";
          ctx.font = "11px Pretendard, system-ui, sans-serif";
          ctx.fillText(p.token, p.x - 12, p.y + 4);
        }
        ctx.globalAlpha = 1;
      }

      if (phase === "converge" || phase === "encapsulate" || phase === "done") {
        const t = Math.min(1, convergePct / 100);
        matchedHubs.forEach((hub, i) => {
          const angle = (i / Math.max(1, matchedHubs.length)) * Math.PI * 2 - Math.PI / 2;
          const r = size * 0.34 * t;
          const x = cx + Math.cos(angle) * r;
          const y = cy + Math.sin(angle) * r;
          const color = KIND_DOT[hub.kind] || "#94a3b8";
          ctx.beginPath();
          ctx.arc(x, y, 5 + hub.score * 3, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.globalAlpha = 0.55 + hub.score * 0.45;
          ctx.fill();
          ctx.globalAlpha = 1;
          if (t > 0.55) {
            ctx.fillStyle = "rgba(226, 232, 240, 0.95)";
            ctx.font = "10px Pretendard, system-ui, sans-serif";
            const label =
              hub.label_ko.length > 8 ? `${hub.label_ko.slice(0, 7)}…` : hub.label_ko;
            ctx.fillText(label, x - 20, y + 18);
          }
        });
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [phase, size, matchedHubs, convergePct]);

  const show =
    phase === "shatter" ||
    phase === "vortex" ||
    phase === "converge" ||
    phase === "encapsulate" ||
    (phase === "done" && matchedHubs.length > 0);

  if (!show) return null;

  return (
    <canvas
      ref={canvasRef}
      className="pd-lattice-overlay"
      width={size}
      height={size}
      aria-hidden
    />
  );
}
