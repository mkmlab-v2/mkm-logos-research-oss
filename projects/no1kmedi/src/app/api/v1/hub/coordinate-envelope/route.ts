import { readFile } from 'fs/promises'
import path from 'path'
import { NextRequest, NextResponse } from 'next/server'

const DEPTH_ALIASES: Record<string, string> = {
  skim: 'skim',
  deep: 'deep',
  hold: 'hold',
}

function envelopeFile(depth: string): string {
  const key = DEPTH_ALIASES[depth] ?? 'skim'
  return path.join(process.cwd(), `public/data/jema_os_coordinate_envelope_${key}_v1.json`)
}

export async function GET(request: NextRequest) {
  const rawDepth = (request.nextUrl.searchParams.get('read_depth') ?? 'skim').toLowerCase()
  const depth = rawDepth in DEPTH_ALIASES ? rawDepth : 'skim'
  const file = envelopeFile(depth)
  try {
    const raw = await readFile(file, 'utf-8')
    return new NextResponse(raw, {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'public, max-age=120',
        'X-Jema-Read-Depth': depth,
      },
    })
  } catch {
    return NextResponse.json(
      { error: 'coordinate_envelope_missing', read_depth: depth, send_gate: 'HOLD' },
      { status: 404 },
    )
  }
}
