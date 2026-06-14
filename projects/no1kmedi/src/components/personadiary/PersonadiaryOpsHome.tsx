"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  createEmptyNorthStarByLane,
  getNorthStarLine,
  localDateString,
  needsPersonadiaryOnboarding,
  NORTH_STAR_LANE_PLACEHOLDERS,
  PERSONADIARY_LANE_LABELS,
  PERSONADIARY_LANES,
  personadiaryPublicPath,
  type PersonadiaryLane,
  type PersonadiaryMobileOpsV1,
  type PersonadiaryWeeklyItem,
} from "@/lib/personadiaryMobileOpsV1";
import { downloadPersonadiaryMobileOpsExport, importPersonadiaryMobileOpsFromJson } from "@/lib/personadiaryMobileOpsStore";
import {
  downloadPersonadiaryBtrackExport,
  PERSONADIARY_BTRACK_EXPORT_HUMAN_GATE_TEXT_KO,
  PERSONADIARY_BTRACK_INBOX_PATH,
} from "@/lib/personadiaryBtrackExportV1";
import { PersonadiaryDailyGuideCards } from "./PersonadiaryDailyGuideCards";
import { PersonadiaryDailyGuideProvider } from "./usePersonadiaryDailyGuide";
import { PersonadiaryGuideLaneHints } from "./PersonadiaryGuideLaneHints";
import { PersonadiaryHygieneHypoPanel } from "./PersonadiaryHygieneHypoPanel";
import { PersonadiaryVoiceDiaryHypoPanel } from "./PersonadiaryVoiceDiaryHypoPanel";
import { PersonadiaryOfflineNotice } from "./PersonadiaryOfflineNotice";
import { PersonadiaryPwaInstallBanner } from "./PersonadiaryPwaInstallBanner";
import { PersonadiaryPwaRegister } from "./PersonadiaryPwaRegister";
import { usePersonadiaryDailyGuidePull } from "./usePersonadiaryDailyGuidePull";
import { usePersonadiaryMobileOps } from "./usePersonadiaryMobileOps";

function newWeeklyId(): string {
  return `w${Date.now().toString(36)}`;
}

export function PersonadiaryOpsHome() {
  const { ops, ready, saving, persist, setActiveLane } = usePersonadiaryMobileOps();
  const guide = usePersonadiaryDailyGuidePull();
  const [diaryDraft, setDiaryDraft] = useState("");
  const [nextDraft, setNextDraft] = useState("");
  const [weeklyDraft, setWeeklyDraft] = useState("");
  const [northDraft, setNorthDraft] = useState<Record<PersonadiaryLane, string>>({
    body: "",
    mind: "",
    work: "",
    rest: "",
  });
  const [onboardNickname, setOnboardNickname] = useState("");
  const [onboardBirthLocal, setOnboardBirthLocal] = useState("");
  const [onboardTz, setOnboardTz] = useState("Asia/Seoul");
  const [exportPiiRedact, setExportPiiRedact] = useState(true);
  const [exportHumanGate, setExportHumanGate] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const homeHref = personadiaryPublicPath("");

  useEffect(() => {
    if (ops?.next_one_action.text) setNextDraft(ops.next_one_action.text);
  }, [ops?.next_one_action.text]);

  useEffect(() => {
    if (!ops?.north_star_by_lane_hypo_v1) return;
    setNorthDraft({
      body: ops.north_star_by_lane_hypo_v1.lanes.body.one_line,
      mind: ops.north_star_by_lane_hypo_v1.lanes.mind.one_line,
      work: ops.north_star_by_lane_hypo_v1.lanes.work.one_line,
      rest: ops.north_star_by_lane_hypo_v1.lanes.rest.one_line,
    });
  }, [ops?.north_star_by_lane_hypo_v1]);

  const showOnboarding = useMemo(
    () => (ops ? needsPersonadiaryOnboarding(ops) : false),
    [ops]
  );

  if (!ready || !ops) {
    return (
      <section className="pd-ops-loading pd-ops-loading--ios" aria-live="polite" aria-busy="true">
        <div className="pd-ops-loading-pulse" aria-hidden="true" />
        <p className="pd-ops-loading-text">기지 불러오는 중…</p>
        <div className="pd-ops-skeleton-group" aria-hidden="true">
          <div className="pd-ops-skeleton pd-ops-skeleton--hero" />
          <div className="pd-ops-skeleton pd-ops-skeleton--segment" />
          <div className="pd-ops-skeleton pd-ops-skeleton--card" />
          <div className="pd-ops-skeleton pd-ops-skeleton--card" />
        </div>
      </section>
    );
  }

  const currentOps = ops;
  const activeNorthStar = getNorthStarLine(currentOps, currentOps.active_lane);

  async function saveNorthStars() {
    const now = new Date().toISOString();
    const base = currentOps.north_star_by_lane_hypo_v1 ?? createEmptyNorthStarByLane();
    const lanes = { ...base.lanes };
    for (const lane of PERSONADIARY_LANES) {
      lanes[lane] = {
        one_line: northDraft[lane].trim().slice(0, 280),
        updated_at_utc: now,
      };
    }
    await persist({
      ...currentOps,
      north_star_by_lane_hypo_v1: { ...base, lanes },
    });
  }

  async function completeOnboarding(skipped: boolean) {
    const now = new Date().toISOString();
    let birth_instant_utc: string | undefined;
    if (!skipped && onboardBirthLocal.trim()) {
      const d = new Date(onboardBirthLocal);
      if (!Number.isNaN(d.getTime())) birth_instant_utc = d.toISOString();
    }
    const north = currentOps.north_star_by_lane_hypo_v1 ?? createEmptyNorthStarByLane();
    const lanes = { ...north.lanes };
    for (const lane of PERSONADIARY_LANES) {
      if (northDraft[lane].trim()) {
        lanes[lane] = {
          one_line: northDraft[lane].trim().slice(0, 280),
          updated_at_utc: now,
        };
      }
    }
    await persist({
      ...currentOps,
      north_star_by_lane_hypo_v1: { ...north, lanes },
      local_birth_profile_v1: {
        schema: "local_birth_profile_v1",
        preview_only: true,
        nickname: onboardNickname.trim().slice(0, 32) || undefined,
        birth_instant_utc,
        iana_tz: onboardTz.trim().slice(0, 64) || "Asia/Seoul",
        onboarding_skipped: skipped,
        updated_at_utc: now,
      },
    });
  }

  async function saveNextOne() {
    await persist({
      ...currentOps,
      next_one_action: {
        ...currentOps.next_one_action,
        text: nextDraft.trim(),
        lane: currentOps.active_lane,
        due_local: localDateString(),
      },
    });
  }

  async function addWeeklyItem() {
    const text = weeklyDraft.trim();
    if (!text || currentOps.weekly_top5.length >= 5) return;
    const item: PersonadiaryWeeklyItem = {
      id: newWeeklyId(),
      text,
      status: "pending",
      lane: currentOps.active_lane,
    };
    setWeeklyDraft("");
    await persist({ ...currentOps, weekly_top5: [...currentOps.weekly_top5, item] });
  }

  async function toggleWeekly(id: string) {
    const weekly_top5 = currentOps.weekly_top5.map((w) =>
      w.id === id ? { ...w, status: w.status === "done" ? "pending" : "done" } : w
    ) as PersonadiaryWeeklyItem[];
    await persist({ ...currentOps, weekly_top5 });
  }

  async function saveDiaryLine() {
    const body = diaryDraft.trim();
    if (!body) return;
    const entry = {
      date_local: localDateString(),
      body,
      lane: currentOps.active_lane,
      synced: false as const,
    };
    const filtered = currentOps.diary_entries_local.filter((e) => e.date_local !== entry.date_local);
    await persist({
      ...currentOps,
      diary_entries_local: [...filtered, entry],
      checkpoints: [
        ...currentOps.checkpoints,
        { ts_utc: new Date().toISOString(), one_line: body.slice(0, 280) },
      ].slice(-64),
    });
    setDiaryDraft("");
  }

  const todayDiary = currentOps.diary_entries_local.find((e) => e.date_local === localDateString());

  return (
    <>
      <PersonadiaryPwaRegister />
      <PersonadiaryOfflineNotice />
      <PersonadiaryPwaInstallBanner />
      <section className="pd-ops-hero" aria-labelledby="pd-ops-title">
        <div className="pd-premium-section-inner">
          <span className="pd-premium-eyebrow">Persona Diary · Pull-first · preview</span>
          <h1 id="pd-ops-title">내 기지</h1>
          <p className="pd-ops-lead">비예측형 인지 방화벽 — 주의력은 Pull로만 회수합니다.</p>
          {activeNorthStar ? (
            <blockquote className="pd-ops-north-hero" aria-live="polite">
              <span className="pd-ops-north-hero-label">
                {PERSONADIARY_LANE_LABELS[currentOps.active_lane]}
              </span>
              <p className="pd-ops-north-hero-text">{activeNorthStar}</p>
            </blockquote>
          ) : (
            <p className="pd-ops-empty pd-ops-north-hero-empty">
              {PERSONADIARY_LANE_LABELS[currentOps.active_lane]} 북극성을 아래에서 설정하면 여기에 표시됩니다.
            </p>
          )}
          <details className="pd-ops-disclosure">
            <summary>격벽·카피 계약</summary>
            <p className="pd-ops-muted pd-non-prediction-contract" data-contract="non_prediction_v1">
              비예측형 성찰 · 명리=오늘의 흐름·질문거리 · 예언·적중·%·운세 단정 없음 · Logos{" "}
              <span className="pd-ops-hypo-tag">[NON_GATING]</span> · v0.9: OS 차단 stub · Phase 2: 레인→시스템
              API
            </p>
            <p className="pd-ops-muted">
              <span className="pd-ops-gate">SEND_GATE: HOLD</span> · {ops.disclaimer_ko}
            </p>
          </details>
        </div>
      </section>

      {showOnboarding && (
        <section className="pd-ops-block pd-ops-onboard" aria-labelledby="pd-onboard-title">
          <div className="pd-premium-section-inner pd-glass pd-ops-card">
            <h2 id="pd-onboard-title">기지 초기 설정 (로컬만)</h2>
            <p className="pd-ops-muted">
              서버 회원가입 없음 · 아래 정보는 IndexedDB에만 저장됩니다.
            </p>
            <label className="pd-ops-field">
              <span>닉네임 (선택)</span>
              <input
                className="pd-ops-input"
                value={onboardNickname}
                onChange={(e) => setOnboardNickname(e.target.value)}
                maxLength={32}
                placeholder="기지"
              />
            </label>
            <label className="pd-ops-field">
              <span>출생 시각 (선택 · 로컬 Pull 가이드용)</span>
              <input
                className="pd-ops-input"
                type="datetime-local"
                value={onboardBirthLocal}
                onChange={(e) => setOnboardBirthLocal(e.target.value)}
              />
            </label>
            <label className="pd-ops-field">
              <span>IANA 시간대</span>
              <input
                className="pd-ops-input"
                value={onboardTz}
                onChange={(e) => setOnboardTz(e.target.value)}
                maxLength={64}
              />
            </label>
            <p className="pd-ops-muted">4레인 북극성 한 줄 · <span className="pd-ops-hypo-tag">[HYPO]</span></p>
            {PERSONADIARY_LANES.map((lane) => (
              <label key={lane} className="pd-ops-field">
                <span>{PERSONADIARY_LANE_LABELS[lane]}</span>
                <input
                  className="pd-ops-input"
                  value={northDraft[lane]}
                  onChange={(e) =>
                    setNorthDraft((prev) => ({ ...prev, [lane]: e.target.value }))
                  }
                  maxLength={280}
                  placeholder={NORTH_STAR_LANE_PLACEHOLDERS[lane]}
                />
              </label>
            ))}
            <div className="pd-ops-row">
              <button
                type="button"
                className="btn btn-primary"
                disabled={saving}
                onClick={() => void completeOnboarding(false)}
              >
                기지 가동
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={saving}
                onClick={() => void completeOnboarding(true)}
              >
                건너뛰기
              </button>
            </div>
          </div>
        </section>
      )}

      <section className="pd-ops-lanes" aria-label="활성 레인">
        <div className="pd-premium-section-inner">
          <p className="pd-ops-segment-label">지금 레인</p>
          <div className="pd-ops-segment" role="tablist" aria-label="4레인">
            {(ops.lanes as PersonadiaryLane[]).map((lane) => (
              <button
                key={lane}
                type="button"
                role="tab"
                aria-selected={ops.active_lane === lane}
                className={
                  ops.active_lane === lane ? "pd-ops-lane pd-ops-lane--active" : "pd-ops-lane"
                }
                onClick={() => setActiveLane(lane)}
              >
                {PERSONADIARY_LANE_LABELS[lane]}
              </button>
            ))}
          </div>
        </div>
      </section>

      {!showOnboarding && (
        <section className="pd-ops-block" aria-labelledby="pd-north-title">
          <div className="pd-premium-section-inner pd-ios-group">
            <p id="pd-north-title" className="pd-ios-group-label">
              북극성 4레인 <span className="pd-ops-hypo-tag">[HYPO]</span>
            </p>
            <p className="pd-ios-group-hint">자기 서술만 · 감시·AI 진단 없음</p>
            <div className="pd-ios-inset pd-ops-card">
              {PERSONADIARY_LANES.map((lane, index) => (
                <label
                  key={lane}
                  className={`pd-ios-row${index < PERSONADIARY_LANES.length - 1 ? " pd-ios-row--divider" : ""}`}
                >
                  <span className="pd-ios-row-label">{PERSONADIARY_LANE_LABELS[lane]}</span>
                  <input
                    className="pd-ios-row-input"
                    value={northDraft[lane]}
                    onChange={(e) =>
                      setNorthDraft((prev) => ({ ...prev, [lane]: e.target.value }))
                    }
                    maxLength={280}
                    placeholder={NORTH_STAR_LANE_PLACEHOLDERS[lane]}
                    aria-label={`${PERSONADIARY_LANE_LABELS[lane]} 북극성`}
                  />
                </label>
              ))}
            </div>
            <button
              type="button"
              className="btn btn-ghost pd-ios-group-action"
              disabled={saving}
              onClick={() => void saveNorthStars()}
            >
              북극성 저장 (로컬)
            </button>
          </div>
        </section>
      )}

      <section className="pd-ops-block" aria-labelledby="pd-next-title">
        <div className="pd-premium-section-inner pd-glass pd-ops-card">
          <h2 id="pd-next-title">지금 1타</h2>
          <input
            className="pd-ops-input"
            value={nextDraft}
            onChange={(e) => setNextDraft(e.target.value)}
            placeholder="지금 당장 하나만"
            maxLength={200}
          />
          <button type="button" className="btn btn-primary" disabled={saving} onClick={saveNextOne}>
            저장 (로컬)
          </button>
        </div>
      </section>

      <section className="pd-ops-block" aria-labelledby="pd-week-title">
        <div className="pd-premium-section-inner pd-glass pd-ops-card">
          <h2 id="pd-week-title">
            이번 주 {ops.week_label} ({ops.weekly_top5.length}/5)
          </h2>
          <ul className="pd-ops-week-list">
            {ops.weekly_top5.length === 0 ? (
              <li className="pd-ops-empty pd-ops-week-empty">
                이번 주 목표가 비어 있습니다. 아래에서 하나만 추가해 보세요.
              </li>
            ) : (
              ops.weekly_top5.map((w) => (
                <li key={w.id}>
                  <button type="button" className="pd-ops-week-check" onClick={() => toggleWeekly(w.id)}>
                    {w.status === "done" ? "✓" : "○"}
                  </button>
                  <span className={w.status === "done" ? "pd-ops-done" : undefined}>
                    [{PERSONADIARY_LANE_LABELS[w.lane]}] {w.text}
                  </span>
                </li>
              ))
            )}
          </ul>
          {ops.weekly_top5.length < 5 && (
            <div className="pd-ops-row">
              <input
                className="pd-ops-input"
                value={weeklyDraft}
                onChange={(e) => setWeeklyDraft(e.target.value)}
                placeholder="주간 목표 추가"
                maxLength={200}
              />
              <button type="button" className="btn btn-ghost" disabled={saving} onClick={addWeeklyItem}>
                추가
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="pd-ops-block" aria-labelledby="pd-pull-title">
        <div className="pd-premium-section-inner pd-glass pd-ops-card">
          <h2 id="pd-pull-title">오늘 가이드 (Pull)</h2>
          <p className="pd-ops-muted">푸시 없음 — 버튼을 눌렀을 때만 인출합니다. [NON_GATING]</p>
          {!guide.pulled ? (
            <div className="pd-ops-empty pd-ops-pull-empty">
              <p>아직 가이드를 인출하지 않았습니다.</p>
              <p className="pd-ops-muted">푸시 없음 — 원할 때만 Pull 하세요.</p>
              <button type="button" className="btn btn-primary" onClick={() => void guide.pull()}>
                가이드 인출
              </button>
            </div>
          ) : (
            <>
              <PersonadiaryDailyGuideProvider packageOverride={guide.pkg}>
                {guide.loading && (
                  <p className="pd-ops-loading-inline" aria-live="polite">
                    가이드 불러오는 중…
                  </p>
                )}
                {guide.error && <p className="pd-ops-error">로드 실패 — 네트워크 확인</p>}
                {guide.pkg && <PersonadiaryDailyGuideCards />}
              </PersonadiaryDailyGuideProvider>
              <PersonadiaryGuideLaneHints pkg={guide.pkg} />
            </>
          )}
        </div>
      </section>

      <PersonadiaryVoiceDiaryHypoPanel
        ops={currentOps}
        onPersist={persist}
        saving={saving}
        onSaved={(body) => setDiaryDraft(body)}
      />

      <section className="pd-ops-block" aria-labelledby="pd-diary-title">
        <div className="pd-premium-section-inner pd-glass pd-ops-card">
          <h2 id="pd-diary-title">한 줄 일기 · 체크포인트</h2>
          {activeNorthStar && (
            <p className="pd-ops-north-hint" aria-live="polite">
              북극성 · {PERSONADIARY_LANE_LABELS[currentOps.active_lane]}: {activeNorthStar}{" "}
              <span className="pd-ops-hypo-tag">[HYPO]</span>
            </p>
          )}
          {todayDiary && (
            <p className="pd-ops-today">
              오늘 저장됨: {todayDiary.body.slice(0, 120)}
              {todayDiary.body.length > 120 ? "…" : ""}
            </p>
          )}
          <textarea
            className="pd-ops-textarea"
            rows={3}
            value={diaryDraft}
            onChange={(e) => setDiaryDraft(e.target.value)}
            placeholder="이 기기에만 저장 · 서버 전송 없음"
            maxLength={2000}
          />
          <div className="pd-ops-row">
            <button type="button" className="btn btn-primary" disabled={saving} onClick={saveDiaryLine}>
              저장
            </button>
          </div>
        </div>
      </section>

      <PersonadiaryHygieneHypoPanel
        ops={currentOps}
        onPersist={persist}
        onPullGuide={() => void guide.pull()}
        saving={saving}
      />

      <section className="pd-ops-block" aria-labelledby="pd-advanced-title">
        <div className="pd-premium-section-inner pd-glass pd-ops-card">
          <details className="pd-ops-advanced">
            <summary id="pd-advanced-title">고급 · 백업 · 연구</summary>

            <h2 id="pd-export-title" className="pd-ops-export-heading">
            내보내기 <span className="pd-ops-hypo-tag">[HYPO · B-track]</span>
          </h2>
          <p className="pd-ops-muted">
            서버 자동 업로드 없음 · SEND_GATE: HOLD · 수동 파일 복사만
          </p>
          <div className="pd-ops-export-block">
            <h3 className="pd-ops-export-sub">전체 백업 (PII 포함 가능)</h3>
            <p className="pd-ops-muted">닉네임·출생·일기 원문 포함 — 기기 이전용</p>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => downloadPersonadiaryMobileOpsExport(currentOps)}
            >
              JSON 전체 백업
            </button>
          </div>
          <div className="pd-ops-export-block">
            <h3 className="pd-ops-export-sub">기기 복원 (로컬 import)</h3>
            <p className="pd-ops-muted">전체 백업 JSON만 — 현재 IndexedDB를 덮어씁니다 · 서버 없음</p>
            <input
              ref={importInputRef}
              type="file"
              accept="application/json,.json"
              className="pd-ops-import-input"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (!file) return;
                void (async () => {
                  setImportError(null);
                  if (
                    !window.confirm(
                      "백업 JSON으로 이 기기의 기지 데이터를 덮어씁니다. 계속할까요?"
                    )
                  ) {
                    return;
                  }
                  try {
                    const text = await file.text();
                    const saved = await importPersonadiaryMobileOpsFromJson(text);
                    await persist(saved);
                  } catch {
                    setImportError("가져오기 실패 — personadiary_mobile_ops_v1 JSON인지 확인하세요.");
                  }
                })();
              }}
            />
            <button
              type="button"
              className="btn btn-ghost"
              disabled={saving}
              onClick={() => importInputRef.current?.click()}
            >
              JSON 가져오기
            </button>
            {importError && <p className="pd-ops-error">{importError}</p>}
          </div>
          <div className="pd-ops-export-block">
            <h3 className="pd-ops-export-sub">B-track 연구용 (비식별)</h3>
            <label className="pd-ops-check">
              <input
                type="checkbox"
                checked={exportPiiRedact}
                onChange={(e) => setExportPiiRedact(e.target.checked)}
              />
              <span>PII redact — 프로필·일기 본문 제거, 레인 통계만</span>
            </label>
            <label className="pd-ops-check">
              <input
                type="checkbox"
                checked={exportHumanGate}
                onChange={(e) => setExportHumanGate(e.target.checked)}
              />
              <span>{PERSONADIARY_BTRACK_EXPORT_HUMAN_GATE_TEXT_KO}</span>
            </label>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!exportHumanGate || exportBusy}
              onClick={() => {
                setExportBusy(true);
                void downloadPersonadiaryBtrackExport(currentOps, {
                  piiRedact: exportPiiRedact,
                  humanGateAck: exportHumanGate,
                }).finally(() => setExportBusy(false));
              }}
            >
              B-track JSON 내보내기
            </button>
            <p className="pd-ops-muted pd-ops-inbox-hint">
              수동 inbox: <code>{PERSONADIARY_BTRACK_INBOX_PATH}</code>
            </p>
            </div>
            <div className="pd-ops-mkmlife-upsell">
              <h2 className="pd-ops-upsell-title">
                mkmlife 심화 <span className="pd-ops-hypo-tag">[NON_GATING · 별 SKU]</span>
              </h2>
              <p className="pd-ops-muted">
                PersonaDiary는 Pull-first 기지 · mkmlife는 유료 원퀘스천 리포트 · DB/API 합선 없음
              </p>
              <a
                className="btn btn-primary"
                href="https://mkmlife.com"
                target="_blank"
                rel="noopener noreferrer"
              >
                mkmlife.com — 심화 리포트
              </a>
            </div>
          </details>
        </div>
      </section>

      <section className="pd-ops-footer-links">
        <div className="pd-premium-section-inner">
          <Link className="btn btn-ghost" href={homeHref}>
            홈으로
          </Link>
        </div>
      </section>
    </>
  );
}
