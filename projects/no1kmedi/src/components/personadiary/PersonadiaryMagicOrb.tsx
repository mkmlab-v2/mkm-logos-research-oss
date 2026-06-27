"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const COLORS: Record<string, string> = {
  verse: "100, 210, 255",
  theme: "255, 214, 10",
  regime: "94, 92, 230",
  era: "191, 90, 242",
};

const LEGEND = [
  { key: "verse", label: "말씀", color: "#64d2ff" },
  { key: "theme", label: "주제", color: "#ffd60a" },
  { key: "regime", label: "흐름", color: "#5e5ce6" },
  { key: "era", label: "시대", color: "#bf5af2" },
] as const;

type Point = { x: number; y: number; z: number; c: string };

export function PersonadiaryMagicOrb({
  size = 300,
  showTone = true,
  showLegend = true,
  showStatus = true,
  onOrbActivate,
  activateLabel = "구슬을 눌러 호흡 맞추기",
  onToneChange,
}: {
  size?: number;
  showTone?: boolean;
  showLegend?: boolean;
  showStatus?: boolean;
  /** Touch/click on orb canvas (ritual gate-in). */
  onOrbActivate?: () => void;
  activateLabel?: string;
  onToneChange?: (enabled: boolean) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ptsRef = useRef<Point[]>([]);
  const rafRef = useRef<number>(0);
  const [status, setStatus] = useState("호흡과 함께 · 준비됨");
  const [toneOn, setToneOn] = useState(false);
  const audioRef = useRef<{
    ctx: AudioContext;
    osc: OscillatorNode;
    gain: GainNode;
  } | null>(null);

  useEffect(() => {
    const cats = ["verse", "theme", "regime", "era"];
    const N = 120;
    const R = 95;
    ptsRef.current = Array.from({ length: N }, (_, i) => {
      const t = Math.random() * Math.PI * 2;
      const p = Math.acos(Math.random() * 2 - 1);
      const c = cats[i % 4];
      return {
        x: R * Math.sin(p) * Math.cos(t),
        y: R * Math.sin(p) * Math.sin(t),
        z: R * Math.cos(p),
        c,
      };
    });
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
    const css = size;
    canvas.width = css * dpr;
    canvas.height = css * dpr;
    canvas.style.width = `${css}px`;
    canvas.style.height = `${css}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const R = 95;
    const F = 220;
    const cx = css / 2;
    const cy = css / 2;

    const draw = () => {
      const pts = ptsRef.current;
      const s = 0.004;
      const cxr = Math.cos(s);
      const sx = Math.sin(s);
      const cyr = Math.cos(s * 1.3);
      const sy = Math.sin(s * 1.3);
      for (const p of pts) {
        const x1 = p.x * cyr - p.z * sy;
        const z1 = p.z * cyr + p.x * sy;
        const y2 = p.y * cxr - z1 * sx;
        const z2 = z1 * cxr + p.y * sx;
        p.x = x1;
        p.y = y2;
        p.z = z2;
      }

      ctx.clearRect(0, 0, css, css);
      const sorted = [...pts].sort((a, b) => b.z - a.z);
      for (const p of sorted) {
        const sc = F / (F + p.z);
        const x = p.x * sc + cx;
        const y = p.y * sc + cy;
        const sz = Math.max(0.6, ((R + p.z) / R) * 2);
        ctx.beginPath();
        ctx.arc(x, y, sz, 0, Math.PI * 2);
        const a = Math.max(0.15, (p.z + R) / (2 * R));
        ctx.fillStyle = `rgba(${COLORS[p.c]},${a})`;
        ctx.fill();
      }
      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [size]);

  const toggleTone = useCallback(async () => {
    if (toneOn && audioRef.current) {
      const { ctx, osc, gain } = audioRef.current;
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      window.setTimeout(() => {
        try {
          osc.stop();
        } catch {
          /* already stopped */
        }
        audioRef.current = null;
        setToneOn(false);
        onToneChange?.(false);
        setStatus("호흡과 함께 · 준비됨");
      }, 450);
      return;
    }

    const Ctx =
      window.AudioContext ||
      (window as Window & { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctx) return;

    const ctx = new Ctx();
    if (ctx.state === "suspended") await ctx.resume();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = 174;
    gain.gain.value = 0.0001;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.04, ctx.currentTime + 1.2);
    audioRef.current = { ctx, osc, gain };
    setToneOn(true);
    onToneChange?.(true);
    setStatus("부드러운 톤 · 호흡에 맞춰");
  }, [toneOn, onToneChange]);

  return (
    <div className="pd-orb-wrap">
      <canvas
        ref={canvasRef}
        className="pd-orb-canvas"
        width={size}
        height={size}
        role={onOrbActivate ? "button" : undefined}
        tabIndex={onOrbActivate ? 0 : undefined}
        aria-label={onOrbActivate ? activateLabel : "마음의 구슬 파티클"}
        onClick={onOrbActivate ? () => onOrbActivate() : undefined}
        onKeyDown={
          onOrbActivate
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onOrbActivate();
                }
              }
            : undefined
        }
      />
      {showLegend ? (
        <div className="pd-orb-legend">
          {LEGEND.map((item) => (
            <span key={item.key}>
              <i style={{ background: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      ) : null}
      {showStatus ? <p className="pd-orb-status">{status}</p> : null}
      {showTone ? (
        <button
          type="button"
          className="pd-orb-tone-btn"
          onClick={() => void toggleTone()}
        >
          {toneOn ? "마음 호흡 톤 끄기" : "마음 호흡 톤 켜기"}
        </button>
      ) : null}
    </div>
  );
}
