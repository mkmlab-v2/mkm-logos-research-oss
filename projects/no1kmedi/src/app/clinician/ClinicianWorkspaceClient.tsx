"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppWorkspaceShell } from "@/components/AppWorkspaceShell";
import { AdvancedConsultForm } from "@/components/AdvancedConsultForm";
import { siteCopy } from "@/content/siteCopy";

const NAV = [
  { id: "assist", label: "임상 보조" },
  { id: "safety", label: "안전·고지" },
] as const;

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
        CDSS 초안은 근거 매핑을 전제로 하며, 최종 진단·처방·기록은 반드시 의료진이 확정합니다.
      </p>
    </div>
  );
}

export function ClinicianWorkspaceClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [assistSessionKey, setAssistSessionKey] = useState(0);
  const [activeId, setActiveId] = useState<string>(() => {
    const p = searchParams.get("panel");
    return p === "safety" ? "safety" : "assist";
  });

  useEffect(() => {
    const p = searchParams.get("panel");
    const next = p === "safety" ? "safety" : "assist";
    setActiveId((cur) => (cur === next ? cur : next));
  }, [searchParams]);

  const onSelect = useCallback(
    (id: string) => {
      setActiveId(id);
      const path = id === "assist" ? "/clinician" : `/clinician?panel=${encodeURIComponent(id)}`;
      router.replace(path, { scroll: false });
    },
    [router],
  );

  const resetAssistForm = useCallback(() => {
    setAssistSessionKey((k) => k + 1);
    if (activeId !== "assist") {
      setActiveId("assist");
      router.replace("/clinician", { scroll: false });
    }
  }, [activeId, router]);

  return (
    <AppWorkspaceShell
      homeHref="/"
      roleLabel="한의사"
      nav={[...NAV]}
      activeId={activeId}
      onSelect={onSelect}
      sidebarFooter={
        <button type="button" className="workspace-secondary-btn" onClick={resetAssistForm}>
          입력 초기화
        </button>
      }
    >
      {activeId === "assist" ? (
        <div className="workspace-scroll-panel">
          <AdvancedConsultForm key={assistSessionKey} />
        </div>
      ) : null}
      {activeId === "safety" ? <ClinicianSafetyPanel /> : null}
    </AppWorkspaceShell>
  );
}
