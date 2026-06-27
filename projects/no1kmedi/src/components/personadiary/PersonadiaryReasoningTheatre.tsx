"use client";

import { useEffect, useRef } from "react";

import {
  hueToRgb,
  PD_REASONING_THEATRE_STEPS,
  type PdReasoningTheatreStep,
  type PdReasoningTheatreStepId,
} from "@/lib/personadiaryReasoningTheatreV1";

type Props = {
  size: number;
  activeStepId: PdReasoningTheatreStepId;
  breathPct?: number;
  layerOpacity?: number;
  className?: string;
  steps?: PdReasoningTheatreStep[];
};

type OrbitParticle = {
  angle: number;
  speed: number;
  size: number;
};

const STEP_EASE_MS = 520;
const INACTIVE_RING_ALPHA = 0.06;
const ACTIVE_PARTICLE_COUNT = 8;

function easeOutCubic(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return 1 - (1 - x) ** 3;
}

export function PersonadiaryReasoningTheatre({
  size,
  activeStepId,
  breathPct = 0,
  layerOpacity = 1,
  className = "",
  steps = PD_REASONING_THEATRE_STEPS,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<OrbitParticle[]>([]);
  const rafRef = useRef<number>(0);
  const t0Ref = useRef(0);
  const stepEaseRef = useRef(1);
  const stepEaseStartRef = useRef(0);
  const lastStepRef = useRef(activeStepId);
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  useEffect(() => {
    if (lastStepRef.current !== activeStepId) {
      lastStepRef.current = activeStepId;
      stepEaseRef.current = 0;
      stepEaseStartRef.current = performance.now();
    }
    particlesRef.current = Array.from({ length: ACTIVE_PARTICLE_COUNT }, (_, i) => ({
      angle: (i / ACTIVE_PARTICLE_COUNT) * Math.PI * 2,
      speed: 0.0032 + i * 0.0004,
      size: 1.1 + (i % 3) * 0.35,
    }));
    t0Ref.current = performance.now();
  }, [activeStepId, steps]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr =
      typeof window !== "undefined" ? Math.min(window.devicePixelRatio || 1, 2) : 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const cx = size / 2;
    const cy = size / 2;
    const baseR = size * 0.34;

    const draw = (now: number) => {
      if (stepEaseRef.current < 1 && !reducedMotion) {
        const t = (now - stepEaseStartRef.current) / STEP_EASE_MS;
        stepEaseRef.current = easeOutCubic(t);
      } else {
        stepEaseRef.current = 1;
      }

      const elapsed = (now - t0Ref.current) / 1000;
      const breath = Math.min(1, breathPct / 100);
      const breatheWave = reducedMotion ? 0 : Math.sin(elapsed * 1.35) * 0.5 + 0.5;
      const pulse = reducedMotion ? 1 : 1 + 0.025 * breatheWave + breath * 0.04;
      const stepBlend = stepEaseRef.current;
      const orbitalDrift = reducedMotion ? 0 : elapsed * 0.08;
      const layer = Math.min(1, Math.max(0, layerOpacity));

      ctx.clearRect(0, 0, size, size);
      ctx.globalAlpha = layer;

      const activeStep = steps.find((s) => s.id === activeStepId);
      if (!activeStep) {
        rafRef.current = requestAnimationFrame(draw);
        return;
      }

      const coreR = baseR * 0.22 * pulse;
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
      coreGrad.addColorStop(0, hueToRgb(activeStep.orbit_hue, 0.2 * stepBlend));
      coreGrad.addColorStop(0.55, hueToRgb(activeStep.orbit_hue, 0.06 * stepBlend));
      coreGrad.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = coreGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
      ctx.fill();

      for (const step of steps) {
        const isActive = step.id === activeStepId;
        const ringR = baseR * (0.58 + step.depth * 0.34) * pulse;
        const tilt = 0.52 + step.depth * 0.12;
        const rot = step.orbit_hue * 0.006 + orbitalDrift * (isActive ? 1 : 0.32);

        ctx.beginPath();
        ctx.ellipse(cx, cy, ringR, ringR * tilt, rot, 0, Math.PI * 2);

        if (isActive) {
          const glowPulse = reducedMotion ? 1 : 0.88 + Math.sin(elapsed * 2.2) * 0.12;
          ctx.shadowBlur = 18 * stepBlend * glowPulse;
          ctx.shadowColor = hueToRgb(step.orbit_hue, 0.35 * glowPulse);
          ctx.strokeStyle = hueToRgb(step.orbit_hue, 0.42 * stepBlend * glowPulse);
          ctx.lineWidth = 1.4;
          ctx.stroke();
          ctx.shadowBlur = 0;
          ctx.strokeStyle = hueToRgb(step.orbit_hue, 0.18 * stepBlend * glowPulse);
          ctx.lineWidth = 4.5;
          ctx.stroke();
        } else {
          ctx.strokeStyle = hueToRgb(step.orbit_hue, INACTIVE_RING_ALPHA);
          ctx.lineWidth = 0.85;
          ctx.stroke();
        }
      }

      if (!reducedMotion) {
        const ringR = baseR * (0.58 + activeStep.depth * 0.34) * pulse;
        const tilt = 0.52 + activeStep.depth * 0.12;

        for (const p of particlesRef.current) {
          p.angle += p.speed;
          const x = cx + Math.cos(p.angle) * ringR;
          const y = cy + Math.sin(p.angle) * ringR * tilt;

          const dotGrad = ctx.createRadialGradient(x, y, 0, x, y, p.size * 2.2);
          dotGrad.addColorStop(0, hueToRgb(activeStep.orbit_hue, 0.75 * stepBlend));
          dotGrad.addColorStop(1, hueToRgb(activeStep.orbit_hue, 0));
          ctx.fillStyle = dotGrad;
          ctx.beginPath();
          ctx.arc(x, y, p.size * 1.6, 0, Math.PI * 2);
          ctx.fill();
        }

        void tilt;
      }

      ctx.globalAlpha = 1;
      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, [size, activeStepId, breathPct, layerOpacity, reducedMotion, steps]);

  return (
    <canvas
      ref={canvasRef}
      className={`pd-reasoning-theatre-canvas ${className}`.trim()}
      aria-hidden="true"
      role="presentation"
    />
  );
}
