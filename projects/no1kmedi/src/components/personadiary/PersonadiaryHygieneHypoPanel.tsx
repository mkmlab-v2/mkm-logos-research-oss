"use client";



import { useEffect, useMemo, useState } from "react";

import {

  createDefaultHygienePrefs,

  isPullWindowNow,

  runLocalHygiene,

  type HygieneRunStats,

  type PersonadiaryHygienePrefsHypoV1,

} from "@/lib/personadiaryHygieneHypoV1";

import type { PersonadiaryMobileOpsV1 } from "@/lib/personadiaryMobileOpsV1";

import {

  detectPersonadiaryRuntime,

  getScreenTimeBridgeStatus,

  NATIVE_SHELL_HYPO_REPO,

} from "@/lib/personadiaryNativeBridgeHypoV1";

import { probeScreenTimeBridgeStub } from "@/lib/personadiaryScreenTimeBridgeStubHypoV1";



type Props = {

  ops: PersonadiaryMobileOpsV1;

  onPersist: (next: PersonadiaryMobileOpsV1) => Promise<PersonadiaryMobileOpsV1 | void>;

  onPullGuide?: () => void;

  saving?: boolean;

};



export function PersonadiaryHygieneHypoPanel({ ops, onPersist, onPullGuide, saving }: Props) {

  const bridge = useMemo(() => getScreenTimeBridgeStatus(), []);

  const screenTimeStub = useMemo(() => probeScreenTimeBridgeStub(), []);

  const runtime = useMemo(() => detectPersonadiaryRuntime(), []);

  const prefs = ops.hygiene_prefs_hypo_v1 ?? createDefaultHygienePrefs();

  const [pullWindow, setPullWindow] = useState(prefs.pull_window_local ?? "21:00");

  const [lastStats, setLastStats] = useState<HygieneRunStats | null>(null);

  const [inWindow, setInWindow] = useState(false);



  useEffect(() => {

    const tick = () => setInWindow(isPullWindowNow(pullWindow));

    tick();

    const id = window.setInterval(tick, 60_000);

    return () => window.clearInterval(id);

  }, [pullWindow]);



  async function savePrefs(nextPrefs: PersonadiaryHygienePrefsHypoV1) {

    await onPersist({

      ...ops,

      hygiene_prefs_hypo_v1: nextPrefs,

      notification_policy: {

        push_enabled: false,

        pull_reminder_local: nextPrefs.pull_window_local ?? "21:00",

      },

      updated_at_utc: new Date().toISOString(),

    });

  }



  return (

    <section className="pd-ops-block pd-ops-native-hypo" aria-labelledby="pd-native-hypo-title">

      <div className="pd-premium-section-inner pd-ios-group">

        <details className="pd-ops-system-details">

          <summary id="pd-native-hypo-title">

            시스템 · Pull · 위생 <span className="pd-ops-hypo-tag">[HYPO]</span>

          </summary>



          <p className="pd-ios-group-hint pd-ops-native-disclaimer">

            푸시 없음 · OS 앱 차단 stub(v0.9) · 서버 업로드 없음

          </p>



          <div className="pd-ios-inset pd-ops-card">

            <div className="pd-ios-row pd-ios-row--static pd-ios-row--divider">

              <span className="pd-ios-row-label">런타임</span>

              <span className="pd-ios-row-value">{runtime}</span>

            </div>

            <div className="pd-ios-row pd-ios-row--static pd-ios-row--divider">

              <span className="pd-ios-row-label">OS 차단</span>

              <span className="pd-ios-row-value">{screenTimeStub.capability}</span>

            </div>

            <div className="pd-ios-row pd-ios-row--static">

              <span className="pd-ios-row-label">브릿지</span>

              <span className="pd-ios-row-value">{bridge.status}</span>

            </div>

          </div>



          <p className="pd-ops-muted pd-ops-native-repo">

            Capacitor PoC: <code>{NATIVE_SHELL_HYPO_REPO}</code>

          </p>



          <div className="pd-ios-inset pd-ops-card">

            <label className="pd-ios-row">

              <span className="pd-ios-row-label">Pull 시간</span>

              <input

                type="time"

                className="pd-ios-row-input pd-ios-row-input--time"

                value={pullWindow}

                onChange={(e) => setPullWindow(e.target.value)}

                onBlur={() => {

                  void savePrefs({

                    ...prefs,

                    pull_window_local: pullWindow,

                    native_shell_target:

                      runtime === "capacitor_webview" ? "capacitor_hypo_v1" : "web_pwa",

                  });

                }}

                aria-label="Pull 선호 시간 (로컬 · 알림 아님)"

              />

            </label>

          </div>



          {inWindow && (

            <p className="pd-ops-hint pd-ops-pull-window-hint">

              Pull 시간대 ±15분 — 가이드를 직접 Pull 하세요 (자동 푸시 없음)

            </p>

          )}



          <div className="pd-ops-native-actions">

            <button

              type="button"

              className="btn btn-ghost"

              disabled={saving}

              onClick={() => {

                void (async () => {

                  const { ops: tidied, stats } = runLocalHygiene(ops);

                  setLastStats(stats);

                  await onPersist({

                    ...tidied,

                    hygiene_prefs_hypo_v1: {

                      ...prefs,

                      pull_window_local: pullWindow,

                      last_hygiene_run_utc: new Date().toISOString(),

                      native_shell_target:

                        runtime === "capacitor_webview" ? "capacitor_hypo_v1" : "web_pwa",

                    },

                    updated_at_utc: new Date().toISOString(),

                  });

                })();

              }}

            >

              로컬 위생 실행

            </button>

            {onPullGuide && (

              <button

                type="button"

                className="btn btn-primary"

                disabled={saving}

                onClick={() => {

                  onPullGuide();

                  void savePrefs({

                    ...prefs,

                    pull_window_local: pullWindow,

                    last_guide_prefetch_utc: new Date().toISOString(),

                    native_shell_target:

                      runtime === "capacitor_webview" ? "capacitor_hypo_v1" : "web_pwa",

                  });

                }}

              >

                가이드 Pull (수동)

              </button>

            )}

          </div>



          {lastStats ? (

            <p className="pd-ops-muted">

              위생: checkpoints {lastStats.checkpoints_before}→{lastStats.checkpoints_after} · diary{" "}

              {lastStats.diary_before}→{lastStats.diary_after}

            </p>

          ) : (

            <p className="pd-ops-empty pd-ops-hygiene-empty">아직 위생 실행 기록이 없습니다.</p>

          )}

        </details>

      </div>

    </section>

  );

}

