'use client'

import { useEffect, useState } from 'react'
import {
  fetchJemaAiHubBrandHandoff,
  type JemaAiHubBrandHandoff,
} from '@/lib/jema-ai-hub-brand-handoff'

type Props = {
  locale?: 'ko' | 'en'
}

export function JemaAiHubBrandHandoffStrip({ locale = 'ko' }: Props) {
  const [handoff, setHandoff] = useState<JemaAiHubBrandHandoff | null>(null)

  useEffect(() => {
    let cancelled = false
    void fetchJemaAiHubBrandHandoff().then((doc) => {
      if (!cancelled) setHandoff(doc)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!handoff) return null

  const en = locale === 'en'
  const disclaimer = en ? handoff.governance.disclaimer_en : handoff.governance.disclaimer_ko
  const pipelineNote = handoff.pipeline_snapshot.hybrid_chain_ok
    ? en
      ? 'Pipeline snapshot connected (read-only)'
      : '파이프라인 스냅샷 연결됨 (읽기 전용)'
    : en
      ? 'Pipeline snapshot pending'
      : '파이프라인 스냅샷 대기'

  const primaryCtas = handoff.cta_links.slice(0, 4)

  return (
    <aside
      className="jema-ai-hub-brand-handoff universe-hub-positioning-strip"
      role="note"
      aria-label={en ? 'JEMA OS hub brand handoff' : 'JEMA OS 허브 브랜드 핸드오프'}
    >
      <p className="jema-ai-hub-brand-handoff__lead">
        <span className="jema-ai-hub-brand-handoff__badge">{handoff.brand.public_os_display}</span>
        <span className="jema-ai-hub-brand-handoff__badge">{handoff.governance.send_gate}</span>
        <span className="jema-ai-hub-brand-handoff__badge">
          {handoff.surface.hub_llm_enabled ? 'HUB-LLM' : 'HUB-LLM-OFF'}
        </span>
        {handoff.brand.hub_display} · {pipelineNote}
      </p>
      <p className="jema-ai-hub-brand-handoff__disclaimer">{disclaimer}</p>
      {primaryCtas.length ? (
        <nav className="hub-cross-links jema-ai-hub-brand-handoff__ctas" aria-label={en ? 'Hub routes' : '허브 분기'}>
          {primaryCtas.map((cta) => {
            const external = cta.href.startsWith('http')
            return (
              <a
                key={cta.key}
                className="hub-pill-link"
                href={cta.href}
                {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                title={cta.sublabel}
              >
                {cta.label}
              </a>
            )
          })}
        </nav>
      ) : null}
    </aside>
  )
}
