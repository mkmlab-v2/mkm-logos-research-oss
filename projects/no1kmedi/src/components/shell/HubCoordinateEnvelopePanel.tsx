'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  fetchCoordinateEnvelope,
  type JemaOsCoordinateEnvelope,
  type JemaOsReadDepth,
} from '@/lib/jema-os-coordinate-envelope'

type Props = {
  locale?: 'ko' | 'en'
  skimLabel: string
  deepLabel: string
  panelNote: string
  holdDisclaimer: string
}

export function HubCoordinateEnvelopePanel({
  locale = 'ko',
  skimLabel,
  deepLabel,
  panelNote,
  holdDisclaimer,
}: Props) {
  const [depth, setDepth] = useState<JemaOsReadDepth>('skim')
  const [envelope, setEnvelope] = useState<JemaOsCoordinateEnvelope | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async (next: JemaOsReadDepth) => {
    setLoading(true)
    const doc = await fetchCoordinateEnvelope(next)
    setEnvelope(doc)
    setLoading(false)
  }, [])

  useEffect(() => {
    void load(depth)
  }, [depth, load])

  if (!envelope && !loading) return null

  const en = locale === 'en'
  const tier = envelope?.umr_binding.resolution_tier ?? '—'
  const ltmDepth = envelope?.umr_binding.required_ltm_depth
  const concept = envelope?.ltm_pin.concept_id ?? '—'
  const a2a = envelope?.a2a_peer?.peer_handoff_pointer

  return (
    <aside
      className="hub-coordinate-envelope"
      role="note"
      aria-label={en ? 'JEMA OS coordinate envelope' : 'JEMA OS 좌표 봉투'}
    >
      <div className="hub-coordinate-envelope__toolbar">
        <span className="hub-coordinate-envelope__label">{panelNote}</span>
        <div className="hub-coordinate-envelope__toggle" role="group" aria-label={en ? 'Read depth' : '읽기 깊이'}>
          <button
            type="button"
            className={`hub-coordinate-envelope__btn${depth === 'skim' ? ' is-active' : ''}`}
            aria-pressed={depth === 'skim'}
            onClick={() => setDepth('skim')}
          >
            {skimLabel}
          </button>
          <button
            type="button"
            className={`hub-coordinate-envelope__btn${depth === 'deep' ? ' is-active' : ''}`}
            aria-pressed={depth === 'deep'}
            onClick={() => setDepth('deep')}
          >
            {deepLabel}
          </button>
        </div>
      </div>
      {envelope ? (
        <p className="hub-coordinate-envelope__meta">
          <span className="hub-coordinate-envelope__badge">{envelope.send_gate}</span>
          <span className="hub-coordinate-envelope__badge">{tier}</span>
          <span className="hub-coordinate-envelope__badge">
            LTM {typeof ltmDepth === 'number' ? ltmDepth.toFixed(2) : '—'}
          </span>
          <span className="hub-coordinate-envelope__mono">{concept}</span>
          {a2a ? (
            <span className="hub-coordinate-envelope__mono" title={a2a}>
              A2A · {en ? 'linked' : '연결'}
            </span>
          ) : null}
        </p>
      ) : null}
      <p className="hub-coordinate-envelope__disclaimer">{holdDisclaimer}</p>
    </aside>
  )
}
