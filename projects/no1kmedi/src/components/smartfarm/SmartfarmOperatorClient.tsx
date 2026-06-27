"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { SmartfarmBrandLogo } from "@/components/smartfarm/SmartfarmBrandLogo";
import { smartfarmOperatorCopy as c } from "@/content/smartfarmOperatorCopy";
import {
  apiBasePath,
  SMARTFARM_PILOT_FARM_ID,
  SMARTFARM_SENSOR_ZONES,
  SMARTFARM_VALVE_CHANNELS,
  type SmartfarmValveChannel,
} from "@/lib/smartfarmOperatorConfig";
import { DEFAULT_HOMEPAGE_PRESET, homepagePresetClassMap } from "@/lib/homepagePreset";

type Telemetry = {
  soil_moisture_pct?: number;
  soil_temp_c?: number;
  soil_ec_us_cm?: number;
  comm_ok?: boolean;
  ts_utc?: string;
};

type ZoneState = {
  telemetry: Telemetry | null;
  daily_runtime_min?: number;
  pending_command_count?: number;
};

type FarmEvent = {
  event_type?: string;
  ts_utc?: string;
  payload?: Record<string, unknown>;
};

type AutoEvaluate = {
  decision?: string;
  reason_code?: string;
  suggested_command?: Record<string, unknown> | null;
};

type ChannelUiState = "unknown" | "open" | "closed";

const POLL_MS = 12_000;
const STALE_SEC = 900;

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { ...init, cache: "no-store" });
  const data = (await res.json()) as T & { error?: string };
  if (!res.ok) {
    throw new Error((data as { error?: string }).error || `http_${res.status}`);
  }
  return data;
}

function formatTs(ts?: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("ko-KR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return ts;
  }
}

function isStaleTelemetry(t: Telemetry | null): boolean {
  if (!t?.ts_utc) return true;
  const age = (Date.now() - new Date(t.ts_utc).getTime()) / 1000;
  return age > STALE_SEC;
}

export function SmartfarmOperatorClient() {
  const presetClass = homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET];
  const base = apiBasePath();

  const [apiOk, setApiOk] = useState(false);
  const [zones, setZones] = useState<Record<string, ZoneState>>({});
  const [events, setEvents] = useState<FarmEvent[]>([]);
  const [channelState, setChannelState] = useState<Record<string, ChannelUiState>>(() =>
    Object.fromEntries(SMARTFARM_VALVE_CHANNELS.map((ch) => [ch.channel_id, "unknown"])),
  );
  const [busyChannel, setBusyChannel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoPreview, setAutoPreview] = useState(false);
  const [autoResult, setAutoResult] = useState<AutoEvaluate | null>(null);
  const [autoBusy, setAutoBusy] = useState(false);

  const openChannels = useMemo(
    () =>
      new Set(
        Object.entries(channelState)
          .filter(([, v]) => v === "open")
          .map(([k]) => k),
      ),
    [channelState],
  );

  const refresh = useCallback(async () => {
    try {
      await fetchJson(`${base}/health`);
      setApiOk(true);
      setError(null);

      const zoneEntries = await Promise.all(
        SMARTFARM_SENSOR_ZONES.map(async (z) => {
          const state = await fetchJson<ZoneState>(
            `${base}/v1/state/${SMARTFARM_PILOT_FARM_ID}/${z.zone_id}`,
          );
          return [z.zone_id, state] as const;
        }),
      );
      setZones(Object.fromEntries(zoneEntries));

      const ev = await fetchJson<{ events: FarmEvent[] }>(
        `${base}/v1/events?farm_id=${SMARTFARM_PILOT_FARM_ID}&limit=12`,
      );
      setEvents(ev.events?.slice().reverse() ?? []);
    } catch (e: unknown) {
      setApiOk(false);
      setError(e instanceof Error ? e.message : "refresh_failed");
    }
  }, [base]);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const sendValve = useCallback(
    async (ch: SmartfarmValveChannel, action: "open" | "close") => {
      setBusyChannel(ch.channel_id);
      setError(null);
      try {
        const res = await fetch("/api/smartfarm/operator/control", {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "x-sf-open-channels": [...openChannels].join(","),
          },
          body: JSON.stringify({
            channel_id: ch.channel_id,
            action,
            requested_by: "operator_ui",
          }),
        });
        const data = (await res.json()) as { ok?: boolean; error?: string };
        if (!res.ok) {
          if (data.error?.startsWith("interlock")) {
            throw new Error(c.errors.interlock);
          }
          throw new Error(data.error || c.errors.control_failed);
        }
        setChannelState((prev) => ({
          ...prev,
          [ch.channel_id]: action === "open" ? "open" : "closed",
        }));
        await refresh();
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : c.errors.control_failed);
      } finally {
        setBusyChannel(null);
      }
    },
    [openChannels, refresh],
  );

  const emergencyStop = useCallback(async () => {
    setError(null);
    for (const ch of SMARTFARM_VALVE_CHANNELS) {
      if (channelState[ch.channel_id] === "open") {
        await sendValve(ch, "close");
      }
    }
    try {
      await fetchJson(`${base}/v1/control`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          farm_id: SMARTFARM_PILOT_FARM_ID,
          zone_id: "zone_01",
          ts_utc: new Date().toISOString(),
          timezone: "Asia/Seoul",
          command_id: `cmd_emergency_${Date.now()}`,
          mode: "remote_manual",
          target: "pump",
          action: "off",
          reason_code: "emergency_stop",
          max_runtime_sec: 30,
          estimated_volume_liter: 0,
          requested_by: "operator_ui",
        }),
      });
      setChannelState(
        Object.fromEntries(SMARTFARM_VALVE_CHANNELS.map((ch) => [ch.channel_id, "closed"])),
      );
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : c.errors.control_failed);
    }
  }, [base, channelState, refresh, sendValve]);

  const runAutoEvaluate = useCallback(async () => {
    setAutoBusy(true);
    setError(null);
    try {
      const result = await fetchJson<AutoEvaluate>(`${base}/v1/auto/evaluate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          farm_id: SMARTFARM_PILOT_FARM_ID,
          zone_id: "zone_01",
          ts_utc: new Date().toISOString(),
          forecast_rain_mm_12h: 0,
          mode: "auto",
          soil_dry_threshold_pct: 23,
          desired_runtime_sec: 600,
        }),
      });
      setAutoResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "auto_evaluate_failed");
    } finally {
      setAutoBusy(false);
    }
  }, [base]);

  useEffect(() => {
    if (!autoPreview) return;
    void runAutoEvaluate();
    const id = window.setInterval(() => void runAutoEvaluate(), 60_000);
    return () => window.clearInterval(id);
  }, [autoPreview, runAutoEvaluate]);

  return (
    <div className={`${presetClass} smartfarm-page sf-operator-page`}>
      <header className="sf-operator-header">
        <div className="sf-operator-header-inner">
          <Link className="sf-brand sf-operator-brand" href="/smartfarm">
            <span className="sf-brand-logo" aria-hidden="true">
              <SmartfarmBrandLogo variant="header" />
            </span>
            <span className="sf-brand-text">
              <span className="sf-brand-title">
                <span className="sf-brand-mkm">MKM</span>
                <span className="sf-brand-line">{c.brand.title}</span>
              </span>
              <small>{c.brand.subtitle}</small>
            </span>
          </Link>
          <div className="sf-operator-status">
            <span
              className={`sf-operator-dot ${apiOk ? "sf-operator-dot--ok" : "sf-operator-dot--bad"}`}
              aria-hidden="true"
            />
            <span>{apiOk ? c.status.connected : c.status.disconnected}</span>
          </div>
        </div>
      </header>

      <main className="sf-operator-main" id="main">
        {error ? (
          <div className="sf-operator-alert" role="alert">
            {error}
          </div>
        ) : null}

        <section className="sf-operator-section" aria-labelledby="sf-op-sensors">
          <h2 id="sf-op-sensors">{c.sections.sensors}</h2>
          <div className="sf-operator-sensor-grid">
            {SMARTFARM_SENSOR_ZONES.map((z) => {
              const st = zones[z.zone_id];
              const t = st?.telemetry ?? null;
              const stale = isStaleTelemetry(t);
              const commBad = t && t.comm_ok === false;
              return (
                <article key={z.zone_id} className="sf-operator-card">
                  <header className="sf-operator-card-head">
                    <strong>{z.label_ko}</strong>
                    <span className="sf-operator-tag">{z.device_nm}</span>
                  </header>
                  {t ? (
                    <dl className="sf-operator-metrics">
                      <div>
                        <dt>{c.sensor.moisture}</dt>
                        <dd>
                          {t.soil_moisture_pct?.toFixed(1) ?? "—"}
                          {c.sensor.unit_moisture}
                        </dd>
                      </div>
                      <div>
                        <dt>{c.sensor.temp}</dt>
                        <dd>
                          {t.soil_temp_c?.toFixed(1) ?? "—"}
                          {c.sensor.unit_temp}
                        </dd>
                      </div>
                      <div>
                        <dt>{c.sensor.ec}</dt>
                        <dd>
                          {t.soil_ec_us_cm?.toFixed(0) ?? "—"}
                          {c.sensor.unit_ec}
                        </dd>
                      </div>
                    </dl>
                  ) : (
                    <p className="sf-operator-muted">{c.sensor.no_data}</p>
                  )}
                  <footer className="sf-operator-card-foot">
                    <span>{formatTs(t?.ts_utc)}</span>
                    {commBad ? (
                      <span className="sf-operator-warn">{c.status.comm_down}</span>
                    ) : stale ? (
                      <span className="sf-operator-warn">{c.status.stale}</span>
                    ) : null}
                  </footer>
                </article>
              );
            })}
          </div>
        </section>

        <section className="sf-operator-section" aria-labelledby="sf-op-valves">
          <div className="sf-operator-section-head">
            <h2 id="sf-op-valves">{c.sections.valves}</h2>
            <p className="sf-operator-muted">{c.valve.pulse_note}</p>
          </div>
          <div className="sf-operator-valve-grid">
            {SMARTFARM_VALVE_CHANNELS.map((ch) => {
              const ui = channelState[ch.channel_id];
              const isFreshNutrient = ch.role === "fresh_water" || ch.role === "nutrient";
              const blockedOpen =
                actionWouldInterlock(ch.channel_id, openChannels) && ui !== "open";
              return (
                <article
                  key={ch.channel_id}
                  className={`sf-operator-valve ${ui === "open" ? "sf-operator-valve--open" : ""}`}
                >
                  <div className="sf-operator-valve-label">
                    <span className="sf-operator-valve-ch">{ch.channel_id}</span>
                    <strong>{ch.label_ko}</strong>
                    {ch.tier === "showroom_demo" ? (
                      <span className="sf-operator-tag">데모</span>
                    ) : ch.tier === "primary_revenue" ? (
                      <span className="sf-operator-tag">본선</span>
                    ) : null}
                  </div>
                  <div className="sf-operator-valve-actions">
                    <button
                      type="button"
                      className="sf-btn sf-btn-primary sf-operator-btn"
                      disabled={busyChannel === ch.channel_id || blockedOpen}
                      onClick={() => void sendValve(ch, "open")}
                      title={blockedOpen ? c.valve.open_blocked : undefined}
                    >
                      {c.valve.open}
                    </button>
                    <button
                      type="button"
                      className="sf-btn sf-btn-ghost sf-operator-btn"
                      disabled={busyChannel === ch.channel_id}
                      onClick={() => void sendValve(ch, "close")}
                    >
                      {c.valve.close}
                    </button>
                  </div>
                  {isFreshNutrient ? (
                    <p className="sf-operator-muted sf-operator-interlock-hint">
                      {c.valve.open_blocked}
                    </p>
                  ) : null}
                </article>
              );
            })}
          </div>
        </section>

        <section className="sf-operator-section" aria-labelledby="sf-op-safety">
          <h2 id="sf-op-safety">{c.sections.safety}</h2>
          <div className="sf-operator-safety-row">
            <button
              type="button"
              className="sf-btn sf-operator-emergency"
              onClick={() => void emergencyStop()}
            >
              {c.safety.emergency}
            </button>
            <p className="sf-operator-muted">{c.safety.emergency_hint}</p>
          </div>
          <div className="sf-operator-auto-row">
            <label className="sf-operator-toggle">
              <input
                type="checkbox"
                checked={autoPreview}
                onChange={(e) => setAutoPreview(e.target.checked)}
              />
              <span>{autoPreview ? c.safety.auto_on : c.safety.auto_off}</span>
            </label>
            <button
              type="button"
              className="sf-btn sf-btn-ghost sf-operator-btn"
              disabled={autoBusy}
              onClick={() => void runAutoEvaluate()}
            >
              {c.auto.evaluate}
            </button>
          </div>
          <p className="sf-operator-muted">{c.safety.manual_only}</p>
          {autoResult ? (
            <div className="sf-operator-auto-result">
              <strong>
                {autoResult.decision === "execute"
                  ? c.auto.decision_execute
                  : c.auto.decision_skip}
              </strong>
              <span>{autoResult.reason_code}</span>
            </div>
          ) : null}
        </section>

        <section className="sf-operator-section" aria-labelledby="sf-op-events">
          <h2 id="sf-op-events">{c.sections.events}</h2>
          <ul className="sf-operator-events">
            {events.length === 0 ? (
              <li className="sf-operator-muted">{c.events.empty}</li>
            ) : (
              events.map((ev, i) => (
                <li key={`${ev.ts_utc}-${i}`}>
                  <time>{formatTs(ev.ts_utc)}</time>
                  <span>{ev.event_type ?? "event"}</span>
                </li>
              ))
            )}
          </ul>
        </section>

        <aside className="sf-operator-disclaimer" aria-labelledby="sf-op-disc">
          <h3 id="sf-op-disc">{c.disclaimer.title}</h3>
          <ul>
            {c.disclaimer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </aside>
      </main>
    </div>
  );
}

function actionWouldInterlock(channelId: string, open: Set<string>): boolean {
  if (channelId === "ch1" && open.has("ch2")) return true;
  if (channelId === "ch2" && open.has("ch1")) return true;
  return false;
}
