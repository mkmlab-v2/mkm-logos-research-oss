"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppWorkspaceShell } from "@/components/AppWorkspaceShell";
import { MinimalClinicianShell } from "@/components/MinimalClinicianShell";
import {
  CLINICIAN_PASTE_CHART_PANEL,
  defaultClinicianPanelForHost,
  JEMA_AI_PUBLIC_ORIGIN,
  normalizeRequestHost,
} from "@/lib/no1kmedi-portal-host";
import { ClinicianPersistedChat } from "@/components/ClinicianPersistedChat";
import { ClinicianEncounterGoldPanel, type PasteChartSessionSyncV1 } from "@/components/ClinicianEncounterGoldPanel";
import { ClinicianSimpleCopilotPanel } from "@/components/ClinicianSimpleCopilotPanel";
import { ClinicianCanvasStudioLayout } from "@/components/clinician/ClinicianCanvasStudioLayout";
import { ClinicianCanvasEmptyLayout } from "@/components/clinician/ClinicianCanvasEmptyLayout";
import { ClinicianThreadRail } from "@/components/ClinicianThreadRail";
import { ClinicianThreadBackupControls } from "@/components/ClinicianThreadBackupControls";
import { JemaWorkspaceCommandPalette, type PaletteAction } from "@/components/JemaWorkspaceCommandPalette";

const panelFallback = (
  <div className="workspace-fallback" role="status" aria-live="polite">
    패널을 불러오는 중…
  </div>
);

const ClinicianConsultContextPanel = dynamic(
  () =>
    import("@/components/ClinicianConsultContextPanel").then((m) => ({
      default: m.ClinicianConsultContextPanel,
    })),
  { loading: () => panelFallback },
);

const PatientCareBundlePreview = dynamic(
  () =>
    import("@/components/PatientCareBundlePreview").then((m) => ({
      default: m.PatientCareBundlePreview,
    })),
  { loading: () => panelFallback },
);
const ClinicianConsultGraphPanel = dynamic(
  () =>
    import("@/components/ClinicianConsultGraphPanel").then((m) => ({
      default: m.ClinicianConsultGraphPanel,
    })),
  { loading: () => panelFallback },
);
const ClinicianGraphConflictSheet = dynamic(
  () =>
    import("@/components/ClinicianGraphConflictSheet").then((m) => ({
      default: m.ClinicianGraphConflictSheet,
    })),
  { loading: () => panelFallback },
);
const ClinicianGraphPilotKpiStrip = dynamic(
  () =>
    import("@/components/ClinicianGraphPilotKpiStrip").then((m) => ({
      default: m.ClinicianGraphPilotKpiStrip,
    })),
  { loading: () => panelFallback },
);
import { siteCopy } from "@/content/siteCopy";
import { markClinicianGraphCdsReady } from "@/lib/clinicianGraphPilotKpiV1";
import { useClinicianThreads } from "@/hooks/useClinicianThreads";
import type { ClinicianChatThread, ClinicianThreadContext } from "@/lib/clinician-chat-types";
import {
  KM_CDS_UI_ANALYTICS_EVENTS_V1,
  trackKmCdsUiEvent,
} from "@/lib/km-cds-ui-analytics-events-v1";
import { loadSavedClinicianEmail, saveClinicianEmail } from "@/lib/clinician-access-v1";

const NAV_BASE = [
  { id: "copilot", label: "진료 분석" },
  { id: "chat", label: "대화" },
  { id: "patient", label: "환자·설정" },
  { id: "bundle", label: "환자 번들" },
  { id: "gold", label: "Paste Chart" },
  { id: "safety", label: "안전·고지" },
] as const;

const NAV_MINIMAL = [...NAV_BASE] as const;

type MemberAccessStatusResponse = {
  success: boolean;
  error?: string;
  payment_status?: string;
  verification_status?: string;
  can_use_pro_clinical_assist?: boolean;
};

function ClinicianSafetyPanel({
  redFlags = [],
  requestId,
}: {
  redFlags?: string[];
  requestId?: string;
}) {
  const [checks, setChecks] = useState({
    notAutoDiagnosis: false,
    reviewedRedFlags: false,
    physicianFinal: false,
  });
  const ready = checks.notAutoDiagnosis && checks.reviewedRedFlags && checks.physicianFinal;

  return (
    <div className="workspace-panel workspace-panel--prose">
      <h2 className="workspace-panel-title">{siteCopy.safety.title}</h2>
      <div className="notice-box">
        <ul>
          {siteCopy.safety.items.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </div>
      {redFlags.length ? (
        <div className="notice-box">
          <strong>Red flags (CDS 봉투)</strong>
          <ul>
            {redFlags.map((flag) => (
              <li key={flag}>{flag}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="workspace-muted">
        CDSS는 보조 도구입니다. 최종 진단·처방·기록은 한의사가 확정합니다. 명리·보조 슬롯은 [HYPO] 참고용입니다.
      </p>
      <div className="consult-signoff-block">
        <strong>원장 sign-off 체크리스트</strong>
        <div className="consult-bundle-options">
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={checks.notAutoDiagnosis}
              onChange={(e) => setChecks((s) => ({ ...s, notAutoDiagnosis: e.target.checked }))}
            />
            자동 확정·자동 처방이 아님을 확인했습니다
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={checks.reviewedRedFlags}
              onChange={(e) => setChecks((s) => ({ ...s, reviewedRedFlags: e.target.checked }))}
            />
            Red flag·주의 사항을 검토했습니다
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              checked={checks.physicianFinal}
              onChange={(e) => setChecks((s) => ({ ...s, physicianFinal: e.target.checked }))}
            />
            최종 판단 책임이 한의사에게 있음을 확인했습니다
          </label>
        </div>
        {ready && requestId ? (
          <p className="consult-source-chip">encounter_ref: {requestId} · sign-off 준비 완료 (번들 탭에서 확정 기록 가능)</p>
        ) : null}
        <ClinicianGraphPilotKpiStrip />
      </div>
    </div>
  );
}

type ClinicianWorkspaceClientProps = {
  /** no1kmedi.com / clinic.* (or localhost dev simulate) — ChatGPT-minimal chrome */
  minimalShell?: boolean;
  /** Request host — drives Paste Chart default on clinic.* / dev clinic simulate */
  requestHost?: string;
};

function resolveClinicianPanel(
  panelParam: string | null,
  fallback: "gold" | "copilot",
): string {
  if (panelParam === "copilot" || panelParam === "patient" || panelParam === "bundle" || panelParam === "gold" || panelParam === "safety") {
    return panelParam;
  }
  if (panelParam === "chat") return "chat";
  return fallback;
}

export function ClinicianWorkspaceClient({
  minimalShell = false,
  requestHost = "",
}: ClinicianWorkspaceClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nav = minimalShell ? NAV_MINIMAL : NAV_BASE;
  const canvasLayout = searchParams.get("canvas") === "1";
  const defaultPanel = defaultClinicianPanelForHost(
    requestHost || (typeof window !== "undefined" ? normalizeRequestHost(window.location.host) : ""),
  );
  const {
    ready,
    threads,
    activeThreadId,
    setActiveThreadId,
    activeThread,
    createThread,
    deleteThread,
    commitThread,
    updateThreadMeta,
    replaceThreads,
  } = useClinicianThreads();

  const [activeId, setActiveId] = useState<string>(() =>
    resolveClinicianPanel(searchParams.get("panel"), defaultPanel),
  );
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [accessEmail, setAccessEmail] = useState("");
  const [accessBusy, setAccessBusy] = useState(false);
  const [accessStatus, setAccessStatus] = useState<MemberAccessStatusResponse | null>(null);
  const [patientCareBundle, setPatientCareBundle] = useState<Record<string, unknown> | null>(null);
  const [urlEmailPrefilled, setUrlEmailPrefilled] = useState(false);

  const canUseAdvancedConsult = accessStatus?.success === true && accessStatus?.can_use_pro_clinical_assist === true;

  useEffect(() => {
    setPatientCareBundle(null);
  }, [activeThreadId, activeThread?.lastCds?.requestId]);

  useEffect(() => {
    const requestId = activeThread?.lastCds?.requestId;
    if (requestId) markClinicianGraphCdsReady(requestId);
  }, [activeThread?.lastCds?.requestId]);

  useEffect(() => {
    const next = resolveClinicianPanel(searchParams.get("panel"), defaultPanel);
    setActiveId((cur) => (cur === next ? cur : next));
  }, [searchParams, defaultPanel]);

  useEffect(() => {
    if (searchParams.get("panel")) return;
    if (defaultPanel !== CLINICIAN_PASTE_CHART_PANEL) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("panel", CLINICIAN_PASTE_CHART_PANEL);
    router.replace(`/clinician?${params.toString()}`, { scroll: false });
  }, [defaultPanel, router, searchParams]);

  useEffect(() => {
    try {
      const k = "mkm_km_cds_clinician_workspace_mount_v1";
      if (typeof sessionStorage !== "undefined" && sessionStorage.getItem(k)) return;
      if (typeof sessionStorage !== "undefined") sessionStorage.setItem(k, "1");
      trackKmCdsUiEvent(KM_CDS_UI_ANALYTICS_EVENTS_V1.CDS_MODE_ENTER, {
        surface: "workspace",
        locale: "ko-KR",
        copy_bundle_id: "km_clinician_workspace_v1",
      });
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toLowerCase().includes("mac");
      if ((isMac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onSelect = useCallback(
    (id: string) => {
      setActiveId(id);
      const path = id === "chat" ? "/clinician" : `/clinician?panel=${encodeURIComponent(id)}`;
      router.replace(path, { scroll: false });
    },
    [router],
  );

  const startNewConsult = useCallback(() => {
    createThread();
    setActiveId("chat");
    router.replace("/clinician", { scroll: false });
  }, [createThread, router]);

  const checkAccessStatus = useCallback(async () => {
    const email = accessEmail.trim().toLowerCase();
    if (!email) {
      setAccessStatus({ success: false, error: "이메일을 입력해 주세요." });
      return;
    }
    setAccessBusy(true);
    try {
      const res = await fetch(`/api/member/access-status?email=${encodeURIComponent(email)}`);
      setAccessStatus((await res.json()) as MemberAccessStatusResponse);
    } catch {
      setAccessStatus({ success: false, error: "권한 정보를 가져오지 못했습니다." });
    } finally {
      setAccessBusy(false);
    }
  }, [accessEmail]);

  useEffect(() => {
    const fromUrl = (searchParams.get("email") || searchParams.get("clinician_email") || "")
      .trim()
      .toLowerCase();
    if (fromUrl) {
      setAccessEmail(fromUrl);
      saveClinicianEmail(fromUrl);
      setUrlEmailPrefilled(true);
      return;
    }
    const saved = loadSavedClinicianEmail().trim().toLowerCase();
    if (saved) {
      setAccessEmail((cur) => cur.trim() || saved);
      setUrlEmailPrefilled(true);
    }
  }, [searchParams]);

  useEffect(() => {
    const email = accessEmail.trim().toLowerCase();
    if (email) saveClinicianEmail(email);
  }, [accessEmail]);

  useEffect(() => {
    if (!urlEmailPrefilled || !accessEmail.trim()) return;
    void checkAccessStatus();
  }, [urlEmailPrefilled, accessEmail, checkAccessStatus]);

  const patchContext = useCallback(
    (patch: Partial<ClinicianThreadContext>) => {
      if (!activeThread) return;
      commitThread({
        id: activeThread.id,
        context: { ...activeThread.context, ...patch },
      });
    },
    [activeThread, commitThread],
  );

  const syncPasteChartSession = useCallback(
    (session: PasteChartSessionSyncV1) => {
      if (!activeThread) return;
      const userTurn = { role: "user" as const, message: session.chartSnippet };
      const assistantTurn = { role: "assistant" as const, message: session.summarySnippet };
      const turns = [...activeThread.turns, userTurn, assistantTurn].slice(-48);
      commitThread({
        id: activeThread.id,
        title: session.title,
        patientLabel: session.patientLabel,
        titlePinned: true,
        turns,
        context: {
          ...activeThread.context,
          ssotSlug: session.slug || activeThread.context.ssotSlug,
          birthInstantUtc: session.birthInstantUtc || activeThread.context.birthInstantUtc,
          ianaTz: session.ianaTz || activeThread.context.ianaTz,
          chiefComplaint: session.chiefComplaint || activeThread.context.chiefComplaint,
        },
      });
      updateThreadMeta(activeThread.id, {
        patientLabel: session.patientLabel,
        title: session.title,
        titlePinned: true,
      });
    },
    [activeThread, commitThread, updateThreadMeta],
  );

  const paletteActions: PaletteAction[] = useMemo(
    () => [
      { id: "copilot", label: "진료 분석", hint: "panel", run: () => onSelect("copilot") },
      { id: "chat", label: "대화", hint: "panel", run: () => onSelect("chat") },
      { id: "patient", label: "환자·설정", hint: "panel", run: () => onSelect("patient") },
      { id: "bundle", label: "환자 번들", hint: "panel", run: () => onSelect("bundle") },
      { id: "gold", label: "Paste Chart", hint: "panel", run: () => onSelect("gold") },
      { id: "safety", label: "안전·고지", hint: "panel", run: () => onSelect("safety") },
      { id: "new", label: "새 상담", hint: "스레드", run: () => startNewConsult() },
      {
        id: "home",
        label: minimalShell ? "브랜드 허브" : "랜딩으로",
        hint: minimalShell ? JEMA_AI_PUBLIC_ORIGIN : "/",
        run: () => {
          if (minimalShell) {
            window.open(JEMA_AI_PUBLIC_ORIGIN, "_blank", "noopener,noreferrer");
            return;
          }
          router.push("/");
        },
      },
    ],
    [minimalShell, onSelect, router, startNewConsult],
  );

  const cdsRedFlags = useMemo(() => {
    const env = activeThread?.lastCds?.envelope;
    if (!env) return [];
    const flags = Array.isArray(env.red_flags_and_escalation)
      ? env.red_flags_and_escalation.filter((x): x is string => typeof x === "string")
      : [];
    const caution = activeThread?.lastCds?.reasoning?.caution;
    if (caution && !flags.includes(caution)) flags.unshift(caution);
    return flags.slice(0, 8);
  }, [activeThread]);

  const importThreads = useCallback(
    (merged: ClinicianChatThread[]) => {
      replaceThreads(merged);
      if (!merged.find((t) => t.id === activeThreadId)) {
        setActiveThreadId(merged[0]?.id ?? null);
      }
    },
    [activeThreadId, replaceThreads, setActiveThreadId],
  );

  const sidebarBody =
    ready && threads.length ? (
      <>
        <ClinicianThreadRail
          threads={threads}
          activeId={activeThreadId}
          onSelect={(id) => {
            setActiveThreadId(id);
            setActiveId("chat");
            router.replace("/clinician", { scroll: false });
          }}
          onDelete={deleteThread}
          onUpdateMeta={updateThreadMeta}
        />
        <ClinicianThreadBackupControls threads={threads} onThreadsImported={importThreads} />
      </>
    ) : null;

  if (!ready || !activeThread) {
    return (
      <div className="workspace-fallback" role="status">
        상담 기록을 불러오는 중…
      </div>
    );
  }

  const draftForBundle = activeThread.lastCds
    ? {
        request_id: activeThread.lastCds.requestId,
        clinical_summary: activeThread.lastCds.clinicalSummary,
        reasoning: activeThread.lastCds.reasoning,
      }
    : null;

  const panelContent = (
    <>
      {activeId === "copilot" ? (
        <div className="workspace-scroll-panel">
          {canvasLayout && activeThread.lastCds?.envelope ? (
            <ClinicianCanvasStudioLayout
              requestId={activeThread.lastCds.requestId}
              envelope={activeThread.lastCds.envelope}
              reasoning={activeThread.lastCds.reasoning}
              clinicalSummary={activeThread.lastCds.clinicalSummary}
              validationOk={activeThread.lastCds.validationOk}
              patientCareBundle={patientCareBundle}
              chat={
                <>
                  <h2 className="workspace-panel-title">Encounter</h2>
                  <p className="workspace-muted">
                    Trust Canvas stub · CDS 봉투 기준 그래프·갈등 시트. 전체 폼은{" "}
                    <button
                      type="button"
                      className="workspace-link-btn"
                      onClick={() => router.replace("/clinician?panel=copilot", { scroll: false })}
                    >
                      클래식 뷰
                    </button>
                  </p>
                  {activeThread.lastCds.clinicalSummary ? (
                    <p className="clinician-canvas-chat-summary">{activeThread.lastCds.clinicalSummary}</p>
                  ) : null}
                </>
              }
            />
          ) : canvasLayout ? (
            <ClinicianCanvasEmptyLayout onOpenChat={() => onSelect("chat")} />
          ) : (
            <>
              <ClinicianSimpleCopilotPanel />
              {activeThread.lastCds?.envelope ? (
                <ClinicianConsultGraphPanel
                  requestId={activeThread.lastCds.requestId}
                  envelope={activeThread.lastCds.envelope}
                  reasoning={activeThread.lastCds.reasoning}
                  patientCareBundle={patientCareBundle}
                />
              ) : null}
            </>
          )}
        </div>
      ) : null}
      {activeId === "chat" ? (
        <div className="workspace-chat-column">
          <ClinicianPersistedChat
            thread={activeThread}
            onCommit={commitThread}
            canUseAdvancedConsult={canUseAdvancedConsult}
            onOpenPatientSettings={() => onSelect("patient")}
            onOpenBundle={() => onSelect("bundle")}
          />
        </div>
      ) : null}
      {activeId === "patient" ? (
        <div className="workspace-scroll-panel">
          <ClinicianConsultContextPanel
            context={activeThread.context}
            onContextChange={patchContext}
            accessEmail={accessEmail}
            onAccessEmailChange={setAccessEmail}
            accessBusy={accessBusy}
            accessStatus={accessStatus}
            onCheckAccess={() => void checkAccessStatus()}
          />
        </div>
      ) : null}
      {activeId === "bundle" ? (
        <div className="workspace-scroll-panel">
          {draftForBundle && activeThread.lastCds?.envelope ? (
            <>
              <PatientCareBundlePreview
                enabled={canUseAdvancedConsult}
                formState={activeThread.context}
                draft={draftForBundle}
                cdsEnvelope={activeThread.lastCds.envelope}
                kmCdsValidationOk={activeThread.lastCds.validationOk}
                onBundleReady={setPatientCareBundle}
              />
              <ClinicianGraphConflictSheet
                requestId={activeThread.lastCds.requestId}
                envelope={activeThread.lastCds.envelope}
                reasoning={activeThread.lastCds.reasoning}
                patientCareBundle={patientCareBundle}
              />
            </>
          ) : (
            <div className="workspace-panel notice-box">
              <p>먼저 「대화」에서 진료 보조 초안을 생성한 뒤, SSOT 봉투가 준비되면 번들을 만들 수 있습니다.</p>
            </div>
          )}
        </div>
      ) : null}
      {activeId === "gold" ? (
        <div className="workspace-scroll-panel">
          <ClinicianEncounterGoldPanel
            clinicianEmail={accessEmail}
            defaultSlug={activeThread.context.ssotSlug || ""}
            birthInstantUtc={activeThread.context.birthInstantUtc || ""}
            ianaTz={activeThread.context.ianaTz || "Asia/Seoul"}
            cdsDraft={draftForBundle}
            patientCareBundle={patientCareBundle}
            onFusionBundleReady={setPatientCareBundle}
            onPasteChartSession={syncPasteChartSession}
          />
        </div>
      ) : null}
      {activeId === "safety" ? (
        <ClinicianSafetyPanel redFlags={cdsRedFlags} requestId={activeThread.lastCds?.requestId} />
      ) : null}
    </>
  );

  return (
    <>
      <JemaWorkspaceCommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} actions={paletteActions} />
      {minimalShell ? (
        <MinimalClinicianShell
          roleLabel="한의사"
          nav={[...nav]}
          activeId={activeId}
          onSelect={onSelect}
          sidebarBody={sidebarBody}
          onNewConsult={startNewConsult}
        >
          {panelContent}
        </MinimalClinicianShell>
      ) : (
        <AppWorkspaceShell
          homeHref="/"
          roleLabel="한의사"
          nav={[...nav]}
          activeId={activeId}
          onSelect={onSelect}
          sidebarBody={sidebarBody}
          sidebarFooter={
            <button type="button" className="workspace-secondary-btn" onClick={startNewConsult}>
              새 상담
            </button>
          }
        >
          {panelContent}
        </AppWorkspaceShell>
      )}
    </>
  );
}
