"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppWorkspaceShell } from "@/components/AppWorkspaceShell";
import { MinimalClinicianShell } from "@/components/MinimalClinicianShell";
import { JEMA_AI_PUBLIC_ORIGIN } from "@/lib/no1kmedi-portal-host";
import { ClinicianPersistedChat } from "@/components/ClinicianPersistedChat";
import { ClinicianThreadRail } from "@/components/ClinicianThreadRail";
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
import { siteCopy } from "@/content/siteCopy";
import { useClinicianThreads } from "@/hooks/useClinicianThreads";
import type { ClinicianThreadContext } from "@/lib/clinician-chat-types";
import {
  KM_CDS_UI_ANALYTICS_EVENTS_V1,
  trackKmCdsUiEvent,
} from "@/lib/km-cds-ui-analytics-events-v1";

const NAV = [
  { id: "chat", label: "대화" },
  { id: "patient", label: "환자·설정" },
  { id: "bundle", label: "환자 번들" },
  { id: "safety", label: "안전·고지" },
] as const;

type MemberAccessStatusResponse = {
  success: boolean;
  error?: string;
  payment_status?: string;
  verification_status?: string;
  can_use_pro_clinical_assist?: boolean;
};

function ClinicianSafetyPanel() {
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
      <p className="workspace-muted">
        CDSS는 보조 도구입니다. 최종 진단·처방·기록은 한의사가 확정합니다. 명리·보조 슬롯은 [HYPO] 참고용입니다.
      </p>
    </div>
  );
}

type ClinicianWorkspaceClientProps = {
  /** no1kmedi.com / clinic.* (or localhost dev simulate) — ChatGPT-minimal chrome */
  minimalShell?: boolean;
};

export function ClinicianWorkspaceClient({ minimalShell = false }: ClinicianWorkspaceClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
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
  } = useClinicianThreads();

  const [activeId, setActiveId] = useState<string>(() => {
    const p = searchParams.get("panel");
    if (p === "patient" || p === "bundle" || p === "safety") return p;
    return "chat";
  });
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [accessEmail, setAccessEmail] = useState("");
  const [accessBusy, setAccessBusy] = useState(false);
  const [accessStatus, setAccessStatus] = useState<MemberAccessStatusResponse | null>(null);

  const canUseAdvancedConsult = accessStatus?.success === true && accessStatus?.can_use_pro_clinical_assist === true;

  useEffect(() => {
    const p = searchParams.get("panel");
    const next = p === "patient" || p === "bundle" || p === "safety" ? p : "chat";
    setActiveId((cur) => (cur === next ? cur : next));
  }, [searchParams]);

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

  const paletteActions: PaletteAction[] = useMemo(
    () => [
      { id: "chat", label: "대화", hint: "panel", run: () => onSelect("chat") },
      { id: "patient", label: "환자·설정", hint: "panel", run: () => onSelect("patient") },
      { id: "bundle", label: "환자 번들", hint: "panel", run: () => onSelect("bundle") },
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

  const sidebarBody =
    ready && threads.length ? (
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
            <PatientCareBundlePreview
              enabled={canUseAdvancedConsult}
              formState={activeThread.context}
              draft={draftForBundle}
              cdsEnvelope={activeThread.lastCds.envelope}
              kmCdsValidationOk={activeThread.lastCds.validationOk}
            />
          ) : (
            <div className="workspace-panel notice-box">
              <p>먼저 「대화」에서 진료 보조 초안을 생성한 뒤, SSOT 봉투가 준비되면 번들을 만들 수 있습니다.</p>
            </div>
          )}
        </div>
      ) : null}
      {activeId === "safety" ? <ClinicianSafetyPanel /> : null}
    </>
  );

  return (
    <>
      <JemaWorkspaceCommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} actions={paletteActions} />
      {minimalShell ? (
        <MinimalClinicianShell
          roleLabel="한의사"
          nav={[...NAV]}
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
          nav={[...NAV]}
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
